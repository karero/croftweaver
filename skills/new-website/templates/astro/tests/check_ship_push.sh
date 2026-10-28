#!/usr/bin/env bash
# Regression guard for the push classifier in scripts/ship.sh.
#
# Nothing else exercises ship.sh — its only real workout is an actual publish, which
# is exactly why its failure messages were wrong three times before this existed. The
# worst of them: a transient `ssh: connect to host github.com port 22: Operation timed
# out` was reported as "'production' has commits that 'main' doesn't have … Do NOT
# force-push", sending the owner hunting for a divergence that did not exist, when the
# right move was simply to run it again. Every scenario below is a failure someone
# actually hit, or one a review of the fix found hiding inside it.
#
# Divergence itself is now decided locally, before the network, by
# `git merge-base --is-ancestor origin/production main` — deterministic, so it needs
# no test beyond "it blocks and never pushes". What is still prose-matching is the
# TRANSPORT half behind it, and that is exactly the kind of code that rots silently:
# an edited regex still runs, still exits, and only lies the next time a publish
# fails. This drives the real ship.sh with a stubbed `git` on PATH and
# asserts, per scenario, the exit code, how many pushes were attempted (the retry
# is only correct for connect-time failures) and which message the owner gets.
#
# The scratch cwd deliberately has no astro.config.mjs: that stops ship.sh right
# after the push, before it polls the live site, so the success cases stay offline.
#
# A second section drives the real ship.sh against REAL git, for the mode that publishes
# GitHub's `main` from a throwaway worktree (`ship.fromGitHub`): a bare repo in a temp folder
# as `origin`, a clone of it as the shared folder, and a tiny committed pre-push gate. Only
# npm, curl, sleep and (for two cases) mktemp are stubbed, so it needs no network either. Its
# case names (S2, S3, …) are the scenarios of the toolkit's plan for that mode
# (docs/reviews/SKILL-PLAN-ship-from-worktree.md in the website-builder repo). Its P cases check
# the last line for a *.pages.dev address and for a real domain, in both modes.
#
# A failing case prints the nested run's output behind "  | ": this file runs inside the
# pre-push gate, and ship.sh reads that gate's output, so a nested line must never pass for
# the outer publish's own (ship.sh leaves those lines out of everything it checks).
#
# template-version: 0.23   (keep in step with scripts/ship.sh's marker)
set -euo pipefail
CDPATH= cd -- "$(dirname -- "$0")/.."
ship="$PWD/scripts/ship.sh"
self="$PWD/tests/$(basename -- "$0")"
# Inside a real publish's pre-push gate in worktree mode, ship.sh hands this down; left set, the
# hooks-setting cases below could not fail.
unset SHIP_KEEP_HOOKS_PATH

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/bin" "$work/teefail" "$work/cwd" "$work/cases" "$work/tmp"
# ship.sh keeps git's output in a temp file after a failed push, so every run here gets a temp
# folder of this file's own, which goes with it.
export TMPDIR="$work/tmp"

# Stub git: canned answers for ship.sh's pre-flight checks, scripted push outcomes.
# Every push is logged so a scenario can assert the refspec as well as the count.
cat > "$work/bin/git" <<'STUB'
#!/bin/bash
SHA=1111111111111111111111111111111111111111
UP="$(cat "$FAKE_DIR/upstream" 2>/dev/null || echo "$SHA")"
# git's own options before the subcommand. `-c` settings are logged, so a scenario can assert
# that every fetch runs with git's housekeeping off.
while :; do
  case "$1" in
    -c) echo "$2" >> "$FAKE_DIR/settings"; shift 2 ;;
    -C) shift 2 ;;
    --no-optional-locks) shift ;;
    *) break ;;
  esac
done
case "$1" in
  hash-object) echo 2222222222222222222222222222222222222222 ;;
  config)
    # ship.fromGitHub, read from the clone's own config only: off unless a scenario sets it.
    case "$*" in
      "config --local --get ship.fromGitHub"|"config --local --bool --get ship.fromGitHub")
        [ -f "$FAKE_DIR/fromgithub" ] || exit 1; echo true ;;
      *) echo "STUB: unexpected git invocation: git $*" >&2; exit 3 ;;
    esac ;;
  rev-parse)
    case "$*" in
      *"--abbrev-ref HEAD"*) echo main ;;
      # A Ctrl-C that ends this git call: a terminate to ship.sh (from the pid file `expect` writes)
      # and the status a killed git leaves. A git folder the lock cannot be made in: read-only.
      *"--git-common-dir"*)
        if [ -f "$FAKE_DIR/stopat-commondir" ]; then kill -TERM "$(cat "$FAKE_DIR/shippid")"; exit 130; fi
        if [ -f "$FAKE_DIR/gitdirro" ]; then mkdir -p "$FAKE_DIR/gitdir-ro"; chmod a-w "$FAKE_DIR/gitdir-ro"; echo "$FAKE_DIR/gitdir-ro"; exit 0; fi
        mkdir -p "$FAKE_DIR/gitdir"; echo "$FAKE_DIR/gitdir" ;;
      # `@{u}` is the branch's GitHub counterpart: absent on a branch never pushed,
      # and a DIFFERENT commit when the two have moved apart.
      *"@{u}"*)
        if [ -f "$FAKE_DIR/stopat-upstream" ]; then kill -TERM "$(cat "$FAKE_DIR/shippid")"; exit 130; fi
        [ -f "$FAKE_DIR/noupstream" ] && exit 1; echo "$UP" ;;
      *"--verify -q origin/production"*) [ -f "$FAKE_DIR/noprod" ] && exit 1; echo "$SHA" ;;
      *) echo "$SHA" ;;
    esac ;;
  status) [ -f "$FAKE_DIR/dirty" ] && echo " M src/pages/index.astro"; exit 0 ;;
  # GitHub's copy of ship.sh, read when this folder's differs (worktree mode). Only the case of a
  # Ctrl-C that ends that read gets here, so that read, exactly, is all this answers.
  cat-file)
    if [ "$*" = "cat-file -p $SHA:scripts/ship.sh" ] && [ -f "$FAKE_DIR/stopat-catfile" ]; then
      kill -TERM "$(cat "$FAKE_DIR/shippid")"; exit 130
    fi
    echo "STUB: unexpected git invocation: git $*" >&2; exit 3 ;;
  fetch)
    echo "${*:2}" >> "$FAKE_DIR/fetchargs"
    n=$(( $(cat "$FAKE_DIR/fetches" 2>/dev/null || echo 0) + 1 ))
    echo "$n" > "$FAKE_DIR/fetches"
    if [ -s "$FAKE_DIR/fetchfail" ] && [ "$n" -le "$(cat "$FAKE_DIR/fetchfail")" ]; then
      # Default to a transport failure; a scenario can supply another reason instead,
      # because WHY the fetch failed decides whether retrying makes any sense.
      if [ -f "$FAKE_DIR/fetcherr" ]; then
        cat "$FAKE_DIR/fetcherr" >&2
      else
        echo "ssh: connect to host github.com port 22: Operation timed out" >&2
      fi
      exit 1
    fi ;;
  merge-base)
    # The argument ORDER carries the meaning here: reversing the two refs inverts the
    # check and would let a diverged production be published. A stub that answers any
    # invocation would keep this gate green through exactly that edit, so refuse
    # anything else loudly instead of answering it.
    case "$*" in
      "merge-base --is-ancestor origin/production $SHA")
        [ -f "$FAKE_DIR/diverged" ] && exit 1 || exit 0 ;;
      "merge-base --is-ancestor @ "*)      # is your copy an ancestor of GitHub's? (behind)
        [ -f "$FAKE_DIR/behind" ] && exit 0 || exit 1 ;;
      "merge-base --is-ancestor "*" @")    # is GitHub's an ancestor of yours? (ahead)
        [ -f "$FAKE_DIR/ahead" ] && exit 0 || exit 1 ;;
      *) echo "STUB: unexpected merge-base invocation: git $*" >&2; exit 3 ;;
    esac ;;
  push)
    echo "$*" >> "$FAKE_DIR/pushes"
    n="$(wc -l < "$FAKE_DIR/pushes" | tr -d ' ')"
    [ -f "$FAKE_DIR/$n.out" ] || n=1
    cat "$FAKE_DIR/$n.out" >&2
    # A stop asked for during the push: a terminate sent to ship.sh alone, as `kill <its pid>`
    # sends one. Its pid comes from the file `expect` writes as it starts it.
    if [ -f "$FAKE_DIR/stop" ]; then kill -TERM "$(cat "$FAKE_DIR/shippid")"; fi
    exit "$(cat "$FAKE_DIR/$n.code")" ;;
  *)
    # No silent success for a subcommand nobody taught this stub. An unmatched `case`
    # exits 0 with empty output, which is exactly the "still runs, still exits, only
    # lies" rot this file exists to catch — so refuse loudly instead.
    echo "STUB: unexpected git invocation: git $*" >&2; exit 3 ;;
esac
STUB
chmod +x "$work/bin/git"

# Stub sleep: the retry path waits 5s, which this gate should not pay for.
printf '#!/bin/sh\nexit 0\n' > "$work/bin/sleep"; chmod +x "$work/bin/sleep"

# Stub curl: this gate must never touch the network. Today the success cases stop
# before ship.sh's live-site poll only because the scratch cwd has no astro.config.mjs
# — an implicit property of how ship.sh looks up the URL, not something this test
# controls. Make it explicit: if that lookup ever becomes repo-relative or gains a
# default, this stub is what stops 24 no-delay requests hitting the production site on
# every push, and turns it into a loud failure instead.
printf '#!/bin/sh\necho "STUB: curl must not run in this gate: $*" >&2\nexit 7\n' > "$work/bin/curl"; chmod +x "$work/bin/curl"

# Stub tee: passes input through but writes no file, as a full temp filesystem would.
printf '#!/bin/sh\ncat\nexit 1\n' > "$work/teefail/tee"; chmod +x "$work/teefail/tee"

mark() { # mark <case> <marker> [count]; sets up a pre-flight condition
  # Defaults to 1 rather than empty: the fetch stub gates on a NON-EMPTY marker, so an
  # omitted count would leave the scenario passing without ever failing a fetch.
  mkdir -p "$work/cases/$1"
  printf '%s' "${3:-1}" > "$work/cases/$1/$2"
}

attempt() { # attempt <case> <n> <exit-status>; git's output for that attempt on stdin
  mkdir -p "$work/cases/$1"
  cat > "$work/cases/$1/$2.out"
  echo "$3" > "$work/cases/$1/$2.code"
}

fail=0 stub_skipped=""

# The marker exists so a site can check whether its copy is current with one grep. Two
# files carry it, so assert they agree rather than trusting a comment to keep them so.
# The SAME extraction on both sides: written differently, a trailing comment on one
# marker line would make the two "disagree" over no real drift. And both must be
# non-empty, or deleting both markers would satisfy the check that exists to prove
# they are there.
version_of() { sed -n 's/^# template-version: *\([^ ]*\).*/\1/p' "$1" | head -1; }
ship_version="$(version_of "$ship")"
gate_version="$(version_of "$self")"
if [ -z "$ship_version" ] || [ -z "$gate_version" ]; then
  echo "✗ ship push gate: a template-version marker is missing (ship.sh: '$ship_version',"
  echo "  this file: '$gate_version'). The marker is how a site checks whether its copy"
  echo "  is current; without it that check silently answers nothing."
  fail=1
elif [ "$ship_version" != "$gate_version" ]; then
  echo "✗ ship push gate: template-version disagrees — ship.sh says '$ship_version',"
  echo "  this file says '$gate_version'. Bump both, or a site grepping either one gets"
  echo "  a different answer about how current it is."
  fail=1
fi

checked=0
expect() { # expect <case> <exit> <pushes> <message-fragment> [extra-PATH-dir]
  checked=$((checked + 1))
  local name="$1" want_exit="$2" want_pushes="$3" marker="$4" extra="${5:-}"
  local dir="$work/cases/$name" log="$work/$name.log" path="$work/bin:$PATH" got_exit pushes
  [ -n "$extra" ] && path="$extra:$path"
  mkdir -p "$dir"; rm -f "$dir/pushes" "$dir/fetches" "$dir/settings" "$dir/fetchargs"; : > "$dir/pushes"
  # The wrapper writes down its pid, then becomes ship.sh, so the pid is ship.sh's (the stub's
  # stop cases signal it).
  ( cd "$work/cwd" && FAKE_DIR="$dir" PATH="$path" bash -c 'echo "$$" > "$FAKE_DIR/shippid"; exec bash "$0"' "$ship" > "$log" 2>&1 ) && got_exit=0 || got_exit=$?
  pushes="$(wc -l < "$dir/pushes" | tr -d ' ')"
  # Every fetch with git's housekeeping off, in both modes: housekeeping can prune, and a prune
  # drops the record of another session's worktree whose folder is only away.
  local fetches settings_off
  fetches="$(cat "$dir/fetches" 2>/dev/null || echo 0)"
  settings_off="$(grep -cxE 'maintenance\.auto=false|gc\.auto=0' "$dir/settings" 2>/dev/null || true)"
  if [ "${settings_off:-0}" != $((fetches * 2)) ]; then
    echo "✗ ship push gate [$name]: $fetches fetch(es), but ${settings_off:-0} of the $((fetches * 2)) housekeeping-off settings"
    echo "  (-c maintenance.auto=false -c gc.auto=0 on every fetch)."; fail=1
  fi
  # A lock is worktree mode's, and its EXIT trap removes it on every way out.
  if [ -e "$dir/gitdir/ship.lock" ]; then
    echo "✗ ship push gate [$name]: the publish lock was left behind ($dir/gitdir/ship.lock)."; fail=1
  fi
  if [ "$got_exit" != "$want_exit" ]; then
    echo "✗ ship push gate [$name]: exit $got_exit, expected $want_exit"; fail=1
  fi
  if [ "$pushes" != "$want_pushes" ]; then
    echo "✗ ship push gate [$name]: $pushes push attempt(s), expected $want_pushes"
    echo "  (the automatic retry is only correct for a failure at connect time —"
    echo "   anything later has already paid for a full build and test run.)"; fail=1
  fi
  # The wording matters: this script exists because the WRONG message was printed on a
  # publish that failed for another reason. But these fragments are English, and this
  # template is meant to be translated — SKILL.md calls a German-only site a normal
  # answer. So the check stays hard by default and names its own escape hatch, rather
  # than leaving a translated site with permanently red CI and no clue why.
  # Anything but empty/0/false/no counts as "skip": someone reaching for this has
  # already read a failure telling them to set it, and `=true` should not silently
  # produce the identical red build a second time.
  local skip_wording=0
  case "${SHIP_GATE_SKIP_WORDING:-}" in ''|0|false|no) skip_wording=0 ;; *) skip_wording=1 ;; esac
  if ! grep -qF "$marker" "$log" && [ "$skip_wording" = 0 ]; then
    echo "✗ ship push gate [$name]: the owner was not told \"$marker\". Got:"
    sed -n -E '/^(✗|⚠)/,$p' "$log" | sed 's/^/  | /'
    echo "  (Translated ship.sh's messages? Update the fragments in this file, or run"
    echo "   with SHIP_GATE_SKIP_WORDING=1 to check behaviour only. Exit codes and push"
    echo "   counts are asserted either way.)"
    fail=1
  fi
  # Whatever the verdict, git's own words must reach the owner — they are the one
  # part of the output that is never a guess.
  for fixture in "$dir/1.out" "$dir/fetcherr"; do
    # fetcherr as well as the push output: checking only the push fixtures left the
    # non-network fetch path free to stop printing git's error with this guard green.
    if [ -f "$fixture" ] && ! grep -qF "$(head -1 "$fixture")" "$log"; then
      echo "✗ ship push gate [$name]: git's own error was swallowed ($(basename "$fixture"))."; fail=1
    fi
  done
  # B10: the success cases stay offline because the scratch cwd has no astro.config.mjs
  # — an emergent property of ship.sh's URL lookup, not a contract. Assert the poll
  # never starts, so a future change that reaches it fails here rather than issuing
  # real requests at the live site, whatever tool it reaches for.
  if [ "$want_exit" = 0 ] && grep -q "Verifying the live site" "$log"; then
    echo "✗ ship push gate [$name]: the live-site poll started — this gate must stay offline."; fail=1
  fi
}

# --- the fetch that everything below depends on -----------------------------------
# Every check that follows reads the remote through a local ref, so a failed fetch must
# stop the publish rather than let them answer confidently from stale information.
mark fetchfail fetchfail 2
expect fetchfail 1 0 "couldn't fetch from GitHub"

# ...and a fetch that only blipped must NOT stop it: that is what the retry is for.
mark fetchblip fetchfail 1
attempt fetchblip 1 0 <<'EOF'
To github.com:you/your-site.git
   1111111..2222222  main -> production
EOF
expect fetchblip 0 1 "✓ Pushed"
# ...and exactly one retry, not more: the push scenarios pin their attempt count for the
# same reason, since "how many times do we try" is a deliberate decision either way.
if [ "$(cat "$work/cases/fetchblip/fetches")" != 2 ]; then
  echo "✗ ship push gate [fetchblip]: $(cat "$work/cases/fetchblip/fetches") fetch attempt(s), expected 2"
  fail=1
fi

# ...but a fetch that failed for a NON-network reason must stop at once. Retrying a
# missing remote or expired credentials just adds a 5s wait to the same failure, and
# announcing it as a network blip is the very misdiagnosis this script exists to stop.
mark fetchbroken fetchfail 2
mkdir -p "$work/cases/fetchbroken"
cat > "$work/cases/fetchbroken/fetcherr" <<'EOF'
fatal: 'origin' does not appear to be a git repository
fatal: Could not read from remote repository
EOF
expect fetchbroken 1 0 "not for a network reason"
if [ "$(cat "$work/cases/fetchbroken/fetches")" != 1 ]; then
  echo "✗ ship push gate [fetchbroken]: $(cat "$work/cases/fetchbroken/fetches") fetch attempt(s), expected 1 (no retry)"
  fail=1
fi

# ...and a fetch failure the classifier does NOT recognise stops too. An unknown
# failure is not evidence of a blip, so it must not buy a retry — this is the branch
# that decides an unfamiliar git error is reported rather than waited on.
mark fetchweird fetchfail 2
mkdir -p "$work/cases/fetchweird"
cat > "$work/cases/fetchweird/fetcherr" <<'EOF'
error: cannot lock ref 'refs/remotes/origin/main': is at 1111111 but expected 2222222
EOF
expect fetchweird 1 0 "not for a network reason"
if [ "$(cat "$work/cases/fetchweird/fetches")" != 1 ]; then
  echo "✗ ship push gate [fetchweird]: $(cat "$work/cases/fetchweird/fetches") fetch attempt(s), expected 1 (no retry)"
  fail=1
fi

# --- your copy vs GitHub's: WHICH WAY they differ decides the advice ---------------
# A plain `!=` cannot tell, and telling someone who is BEHIND to "git push" sends them
# to the one command that cannot help. These three assert the direction is read.
mark behind upstream 2222222222222222222222222222222222222222
mark behind behind
expect behind 1 0 "GitHub has changes that aren't on your computer yet"

mark ahead upstream 2222222222222222222222222222222222222222
mark ahead ahead
expect ahead 1 0 "Your latest changes aren't uploaded yet"

mark bothmoved upstream 2222222222222222222222222222222222222222
expect bothmoved 1 0 "BOTH changed"

# --- a brand-new site whose branch has never been pushed --------------------------
mark noupstream noupstream
expect noupstream 1 0 "isn't connected to GitHub yet"

# --- a two-stage site that isn't set up as one: the guard must be able to fire ----
mark noprod noprod
expect noprod 1 0 "isn't set up two-stage"

# --- a changed host key is a SECURITY signal, never a blip to retry ---------------
# Both of these end in "fatal: Could not read from remote repository", so without the
# pre-filter the network arm claims them and tells the owner to just run it again —
# which for a possible machine-in-the-middle is the worst advice available.
attempt hostkey 1 1 <<'EOF'
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
Host key verification failed.
fatal: Could not read from remote repository.
EOF
expect hostkey 1 1 "can't name"

# --- an HTTPS credential failure: the fetch path filtered it, the push path did not
attempt httpsauth 1 1 <<'EOF'
fatal: Authentication failed for 'https://github.com/you/your-site.git/'
fatal: Could not read from remote repository.
EOF
expect httpsauth 1 1 "can't name"

# --- provenance: a line's SHAPE is not its AUTHOR --------------------------------
# The gate's output shares this log with git's. Anchoring proves a line looks like a
# transport error or a rejection; only the gate's own markers prove who wrote it. If
# the gate ran and did not pass, the push never reached the network.
attempt gatequotesssh 1 1 <<'EOF'
▶ pre-push gate: tests…
  ✘ 7 [chromium] › tests/links.spec.ts:9:3 › the docs page's git troubleshooting block renders
    Error: expected page to contain the sample error, got:
ssh: connect to host github.com port 22: Operation timed out
  42 tests, 1 failed
error: failed to push some refs to 'github.com:you/your-site.git'
EOF
expect gatequotesssh 1 1 "can't name"

attempt gatequoteshint 1 1 <<'EOF'
▶ pre-push gate: tests…
  ✘ 8 [chromium] › tests/tone.spec.ts:52:3 › no banned phrasing on /blog/git-for-beginners
    Error: banned phrase found. Page text was:
hint: Updates were rejected because the tip of your current branch is behind
  42 tests, 1 failed
error: failed to push some refs to 'github.com:you/your-site.git'
EOF
expect gatequoteshint 1 1 "can't name"

# --- a genuine divergence: answered locally, so NO push is attempted ------------
# This is the case the scary message is written for, and the check that decides it
# runs off the fetch above — before the network, so a transport failure can never be
# mistaken for it. Zero push attempts is the assertion that matters here.
mkdir -p "$work/cases/diverged"; : > "$work/cases/diverged/diverged"
expect diverged 1 0 "Publish blocked"

# --- production moves DURING the publish: the race the local check can't cover ---
attempt raced 1 1 <<'EOF'
To github.com:you/your-site.git
 ! [rejected]        main -> production (non-fast-forward)
error: failed to push some refs to 'github.com:you/your-site.git'
hint: Updates were rejected because the tip of your current branch is behind
EOF
expect raced 1 1 "moved while this was publishing"

# --- the 2026-08-20 incident, verbatim: must NOT read as a divergence -----------
attempt sshtimeout 1 1 <<'EOF'
ssh: connect to host github.com port 22: Operation timed out
fatal: Could not read from remote repository.
EOF
expect sshtimeout 1 2 "not a branch problem"

# --- a blip that clears: the retry is the whole point of classifying it ---------
attempt sshthenok 1 1 <<'EOF'
ssh: connect to host github.com port 22: Operation timed out
fatal: Could not read from remote repository.
EOF
attempt sshthenok 2 0 <<'EOF'
To github.com:you/your-site.git
   16bf04a..5e78e56  main -> production
EOF
expect sshthenok 0 2 "✓ Pushed"

# --- the retry connects, and then the gate goes red: `kind` must be reassigned ---
# The only path where the classification changes between loop iterations. Getting it
# wrong means a red test suite reported as "couldn't reach GitHub, run it again".
attempt blipthengate 1 1 <<'EOF'
ssh: connect to host github.com port 22: Operation timed out
fatal: Could not read from remote repository.
EOF
attempt blipthengate 2 1 <<'EOF'
▶ pre-push gate: tests…
  Error: page.goto: Timeout 30000ms exceeded. Navigation timed out.
  42 tests, 1 failed
error: failed to push some refs to 'github.com:you/your-site.git'
EOF
expect blipthengate 1 2 "can't name"

# --- other transports, same verdict --------------------------------------------
attempt kexclosed 1 1 <<'EOF'
kex_exchange_identification: Connection closed by remote host
Connection closed by 140.82.121.4 port 22
fatal: Could not read from remote repository.
EOF
expect kexclosed 1 2 "not a branch problem"

attempt dnsfail 1 1 <<'EOF'
fatal: unable to access 'https://github.com/you/your-site.git/': Could not resolve host: github.com
EOF
expect dnsfail 1 2 "not a branch problem"

# --- dropped MID-transfer: the ref may already have landed, so no guessing ------
# and no retry — by this point the pre-push gate has already run for real.
attempt dropped 1 1 <<'EOF'
Writing objects: 100% (7/7), 640 bytes | 640.00 KiB/s, done.
error: RPC failed; curl 56 Recv failure: Connection reset by peer
fatal: the remote end hung up unexpectedly
EOF
expect dropped 1 1 "may or may not have completed"

# --- a red pre-push gate is not a network problem and not a divergence ----------
attempt hookfail 1 1 <<'EOF'
▶ pre-push gate: tests…
  Error: page.goto: Timeout 30000ms exceeded. Navigation timed out.
  42 tests, 1 failed
error: failed to push some refs to 'github.com:you/your-site.git'
EOF
expect hookfail 1 1 "can't name"

# --- and a red gate whose OUTPUT quotes git advice still isn't a divergence -----
# This is why the patterns are anchored to the lines git itself emits: the gate's
# build and test output lands in the same log the classifier reads.
attempt gatequotesgit 1 1 <<'EOF'
▶ pre-push gate: tests…
  ✘ 12 [chromium] › tests/tone.spec.ts:52:3 › tone — no banned phrasing on /blog/git-for-beginners
    Error: banned phrase found. Page text was:
      "…if your push is rejected, fetch first, then push again…"
error: failed to push some refs to 'github.com:you/your-site.git'
EOF
expect gatequotesgit 1 1 "can't name"

# --- an access problem: real, but "run it again" would be its own misdiagnosis --
attempt nokey 1 1 <<'EOF'
git@github.com: Permission denied (publickey).
fatal: Could not read from remote repository.
EOF
expect nokey 1 1 "can't name"

# --- GitHub's ACTUAL permission wording, which says neither "Permission denied" ---
# nor anything network-ish. It ends in "Could not read from remote repository" like
# every other access failure, so before the auth list covered it the network arm
# claimed it and retried. Found by review after the list was in four repos.
attempt permdenied 1 1 <<'EOF'
ERROR: Permission to you/your-site.git denied to someone-else.
fatal: Could not read from remote repository.
EOF
expect permdenied 1 1 "can't name"

# --- mid-transfer disconnects, one alternative per fixture so either breaking shows
attempt rpconly 1 1 <<'EOF'
Enumerating objects: 12, done.
error: RPC failed; curl 92 HTTP/2 stream 5 was not closed cleanly
EOF
expect rpconly 1 1 "may or may not have completed"

attempt sendpackonly 1 1 <<'EOF'
Writing objects: 100% (7/7), done.
send-pack: unexpected disconnect while reading sideband packet
EOF
expect sendpackonly 1 1 "may or may not have completed"

# --- "error: RPC failed" is an UMBRELLA: HTTP 401/403 wear it too, and they are not
# transient. Requiring curl's own error number after the semicolon tells them apart.
# 413 rather than 403 on purpose: a 403 also prints "Authentication failed", which the
# auth arm catches anyway, so it would not isolate this. A payload-too-large has no auth
# line at all — with the umbrella pattern it read as a mid-transfer drop.
attempt rpc413 1 1 <<'EOF'
error: RPC failed; HTTP 413 curl 22 The requested URL returned error: 413
EOF
expect rpc413 1 1 "can't name"

# --- a persistent protocol fault is a configuration problem, not a blip -----------
attempt protocolfault 1 1 <<'EOF'
fatal: protocol error: bad line length character: Inva
EOF
expect protocolfault 1 1 "can't name"

# --- the credential wording that had no fixture. It guards the arm rather than proving
# the new alternative: "Authentication failed" on the next line already matched.
attempt badcreds 1 1 <<'EOF'
remote: Invalid username or password.
fatal: Authentication failed for 'https://github.com/you/your-site.git/'
fatal: Could not read from remote repository.
EOF
expect badcreds 1 1 "can't name"

# --- S1: the setting off, a page edited but not saved: today's stop, unchanged -----
# The worktree mode is opt-in, read from the clone's own config. Without it the folder check
# still catches the owner's forgotten edit, with today's message, which names no setting.
mark dirty dirty
expect dirty 1 0 "You have unsaved changes"
if grep -q 'fromGitHub' "$work/dirty.log"; then
  echo "✗ ship push gate [dirty]: the stop for unsaved changes mentions the setting; a fresh clone should not be steered to it."; fail=1
fi

# --- S5: the setting on, GitHub unreachable on both tries --------------------------
# Today's message, but about this folder: in that mode it is never touched. The fetch names
# its two branches, so a narrowed fetch setting in the clone cannot leave origin/main stale.
mark wtfetchfail fromgithub
mark wtfetchfail fetchfail 2
expect wtfetchfail 1 0 "this folder was not touched"
if ! grep -qF "couldn't fetch from GitHub" "$work/wtfetchfail.log"; then
  echo "✗ ship push gate [wtfetchfail]: not today's fetch message."; fail=1
fi
if [ "$(grep -c "^-q origin +refs/heads/main:refs/remotes/origin/main +refs/heads/production:refs/remotes/origin/production\$" "$work/cases/wtfetchfail/fetchargs")" != 2 ]; then
  echo "✗ ship push gate [wtfetchfail]: the fetch did not name main and production, forced:"
  sed 's/^/  | /' "$work/cases/wtfetchfail/fetchargs"; fail=1
fi

# --- a Ctrl-C that ends a git call before the push ----------------------------------
# Its failure must not read as a verdict about the branches ("isn't connected to GitHub yet"),
# and one that ends the run through set -e must not end it without a word.
mark stopverdict stopat-upstream
expect stopverdict 1 0 "a stop was asked for"
if grep -q "isn't connected to GitHub yet" "$work/stopverdict.log"; then
  echo "✗ ship push gate [stopverdict]: a git call ended by a stop was read as a verdict about the branch."; fail=1
fi
mark stopsilent fromgithub
mark stopsilent stopat-commondir
expect stopsilent 130 0 "Nothing was published and this folder was not touched."
if ! grep -q "a stop was asked for" "$work/stopsilent.log"; then
  echo "✗ ship push gate [stopsilent]: a stop that ended a git call ended the run without saying so."; fail=1
fi

# ...and in worktree mode, one that ends the read of GitHub's copy of ship.sh: not a verdict
# about the two scripts.
mark stopcatfile fromgithub
mark stopcatfile stopat-catfile
expect stopcatfile 1 0 "a stop was asked for"
if grep -q "is not the one on GitHub's main" "$work/stopcatfile.log"; then
  echo "✗ ship push gate [stopcatfile]: a read ended by a stop was taken for two different scripts."; fail=1
fi

# --- worktree mode, a git folder the lock cannot be made in ------------------------
# Not "another publish holds the lock", with a command to remove one that does not exist.
mark lockro fromgithub
mark lockro gitdirro
if [ -w "$work/cases/lockro" ] && mkdir "$work/cases/lockro/w-probe" 2>/dev/null && chmod a-w "$work/cases/lockro/w-probe" \
   && ! mkdir "$work/cases/lockro/w-probe/x" 2>/dev/null; then
  expect lockro 1 0 "couldn't create this clone's publish lock"
  if grep -q "another publish holds" "$work/lockro.log"; then
    echo "✗ ship push gate [lockro]: a lock that could not be made was reported as another publish's."; fail=1
  fi
else
  echo "  note: [lockro] skipped: a read-only folder does not stop this user (root?), so the case cannot be set up."
  stub_skipped="lockro (a read-only folder stops nobody here)"
fi
chmod -R u+w "$work/cases/lockro" 2>/dev/null || true

# --- production moved WHILE the gate ran: the remote refuses the update ------------
# git checked production when the push started, so it sends the update; the remote then finds
# production somewhere else. Stock git's two wordings: git 2.33's, then the newer git's on
# GitHub's runners (seen in this file's own CI). GitHub's is not checked.
attempt reflock 1 1 <<'EOF'
▶ pre-push gate: check, build and tests (scripts/verify.mjs)…
✓ pre-push gate passed — pushing.
remote: error: cannot lock ref 'refs/heads/production': is at 3333333333333333333333333333333333333333 but expected 1111111111111111111111111111111111111111
To github.com:you/your-site.git
 ! [remote rejected] 1111111111111111111111111111111111111111 -> production (failed to update ref)
error: failed to push some refs to 'github.com:you/your-site.git'
EOF
expect reflock 1 1 "moved while this was publishing"
attempt reflocknew 1 1 <<'EOF'
▶ pre-push gate: check, build and tests (scripts/verify.mjs)…
✓ pre-push gate passed — pushing.
remote: error: cannot lock ref 'refs/heads/production': is at 3333333333333333333333333333333333333333 but expected 1111111111111111111111111111111111111111
To github.com:you/your-site.git
 ! [remote rejected] 1111111111111111111111111111111111111111 -> production (incorrect old value provided)
error: failed to push some refs to 'github.com:you/your-site.git'
EOF
expect reflocknew 1 1 "moved while this was publishing"
# ...but git 2.33's "failed to update ref" also covers a ref the remote could not write for
# another reason (here a full disk): without the line saying production is elsewhere, it is
# not a race, and "run it again" would be the wrong advice.
attempt reflockother 1 1 <<'EOF'
▶ pre-push gate: check, build and tests (scripts/verify.mjs)…
✓ pre-push gate passed — pushing.
remote: error: unable to write file ./objects/ab/cdef: No space left on device
To github.com:you/your-site.git
 ! [remote rejected] 1111111111111111111111111111111111111111 -> production (failed to update ref)
error: failed to push some refs to 'github.com:you/your-site.git'
EOF
expect reflockother 1 1 "can't name"
if grep -q "moved while this was publishing" "$work/reflockother.log"; then
  echo "✗ ship push gate [reflockother]: a ref the remote could not write was read as production moving."; fail=1
fi
# The same rule for the newer wording: without the line saying production is elsewhere, the
# refusal proves no race either.
attempt reflocknewother 1 1 <<'EOF'
▶ pre-push gate: check, build and tests (scripts/verify.mjs)…
✓ pre-push gate passed — pushing.
To github.com:you/your-site.git
 ! [remote rejected] 1111111111111111111111111111111111111111 -> production (incorrect old value provided)
error: failed to push some refs to 'github.com:you/your-site.git'
EOF
expect reflocknewother 1 1 "can't name"
if grep -q "moved while this was publishing" "$work/reflocknewother.log"; then
  echo "✗ ship push gate [reflocknewother]: a refusal with no line saying production moved was read as a race."; fail=1
fi

# --- a red gate whose output holds a NESTED run's lines: they change nothing --------
# This file runs inside the gate, and prints a failing case's nested ship output behind
# "  | ". A nested login failure, refusal, port line and pass line are not this publish's.
attempt nested 1 1 <<'EOF'
▶ pre-push gate: publish classifier…
✗ ship push gate [okpush]: exit 1, expected 0
  | ▶ pre-push gate: tests…
  | ✓ pre-push gate passed — pushing.
  | remote: Invalid username or password.
  |  ! [remote rejected] 1111111111111111111111111111111111111111 -> production (failed to update ref)
  | Error: http://localhost:4387 is already used, make sure that nothing is running on the port/url or set reuseExistingServer:true in config.webServer.
error: failed to push some refs to 'github.com:you/your-site.git'
EOF
expect nested 1 1 "can't name"
if grep -qE "test port was taken|moved while" "$work/nested.log"; then
  echo "✗ ship push gate [nested]: a nested run's line was read as this publish's:"
  grep -E "test port was taken|moved while" "$work/nested.log" | sed 's/^/  | /'; fail=1
fi

# --- ...while the gate's OWN port line is named: a test port that another run already holds
attempt portused 1 1 <<'EOF'
▶ pre-push gate: check, build and tests (scripts/verify.mjs)…
Error: http://localhost:4387 is already used, make sure that nothing is running on the port/url or set reuseExistingServer:true in config.webServer.
error: failed to push some refs to 'github.com:you/your-site.git'
EOF
expect portused 1 1 "test port was taken"

# --- a stop during the push (a terminate sent to ship.sh alone) --------------------
# ship.sh notes it and reads git's result as the push step wrote it. A push that went out
# says so; a red gate's log proves nothing after a stop (its pass line may never have been
# written), so that one may or may not have landed; a login failure rests on git's own words.
mkdir -p "$work/cases/stopok"; : > "$work/cases/stopok/stop"
attempt stopok 1 0 <<'EOF'
▶ pre-push gate: check, build and tests (scripts/verify.mjs)…
✓ pre-push gate passed — pushing.
To github.com:you/your-site.git
   16bf04a..5e78e56  1111111111111111111111111111111111111111 -> production
EOF
expect stopok 1 1 "The publish went out"

mkdir -p "$work/cases/stopgate"; : > "$work/cases/stopgate/stop"
attempt stopgate 1 1 <<'EOF'
▶ pre-push gate: check, build and tests (scripts/verify.mjs)…
error: failed to push some refs to 'github.com:you/your-site.git'
EOF
expect stopgate 1 1 "may or may not have landed"

mkdir -p "$work/cases/stopauth"; : > "$work/cases/stopauth/stop"
attempt stopauth 1 1 <<'EOF'
git@github.com: Permission denied (publickey).
fatal: Could not read from remote repository.
EOF
expect stopauth 1 1 "trying"
if grep -q "may or may not" "$work/stopauth.log"; then
  echo "✗ ship push gate [stopauth]: a login failure after a stop read as 'may or may not have landed'."; fail=1
fi

# ...and a connect-time failure after a stop is not retried: the stop was asked for.
mkdir -p "$work/cases/stopnet"; : > "$work/cases/stopnet/stop"
attempt stopnet 1 1 <<'EOF'
ssh: connect to host github.com port 22: Operation timed out
fatal: Could not read from remote repository.
EOF
expect stopnet 1 1 "not a branch problem"

# --- a clean publish -----------------------------------------------------------
attempt okpush 1 0 <<'EOF'
To github.com:you/your-site.git
   16bf04a..5e78e56  main -> production
EOF
expect okpush 0 1 "✓ Pushed"

# ...and the same push when tee fails. `tee` sits in the pipeline, so pipefail
# reports a SUCCESSFUL push as a failure unless git's own status is read.
# Announcing "nothing was published" after the site has gone live is the worst
# lie this script can tell, so it gets its own case.
expect okpush 0 1 "✓ Pushed" "$work/teefail"

# --- nothing but the checked commit may ever be pushed to the live branch --------
# The commit id ship.sh checked, read once: a commit landing on main mid-publish must not
# change what is pushed. And straight to the remote branch: a local checkout of production
# is what the no-checkout push exists to avoid.
okpush_want="push origin 1111111111111111111111111111111111111111:refs/heads/production"
if [ "$(cat "$work/cases/okpush/pushes")" != "$okpush_want" ]; then
  echo "✗ ship push gate: ship.sh pushed '$(cat "$work/cases/okpush/pushes")',"
  echo "  expected exactly '$okpush_want'."
  fail=1
fi

# --- no line in ship.sh may replace its shell --------------------------------------
# Its EXIT trap removes the worktree and the lock, and a shell replaced by another program never
# runs it. Banned outright, comments included, though a redirect-only use would keep the trap:
# the script needs none, and a rule with no exceptions needs no judging.
if grep -nwE 'exec' "$ship" >/dev/null; then
  echo "✗ ship push gate: scripts/ship.sh uses 'exec', which can replace the shell and skip its EXIT trap:"
  grep -nwE 'exec' "$ship" | sed 's/^/  | /'; fail=1
fi

# === The mode that publishes GitHub's main, against real git ===========================
# What the stubbed cases above cannot show: what git itself does with the worktree, the lock,
# the hook, the fetch and a signal. A bare repo in a temp folder is `origin`; a clone of it is
# the shared folder; a seed repo plays whoever else pushes to GitHub's main. The site's
# committed pre-push hook is a tiny gate that prints this kit's own two gate lines and does
# what a case asks of it. Every case asserts the exit status, production's commit, what was
# printed, and that the run left this folder's branch, status and index as they were and no
# lock, worktree or line of ship's own list behind (but a run killed hard, which is the case
# that leaves them).
real_git_cases() {
  rg_n=0 rg_skipped=""
  local gv REAL_SLEEP NODE PERL ps_starts G
  # skip_all <why>: none of these cases can run here. Said out loud, and a failure where CI
  # requires the bash 3.2 case.
  skip_all() {
    rg_skipped="$1: not run"
    echo "  note: the checks of the mode that publishes GitHub's main were not run: $1."
    if [ -n "${SHIP_TEST_REQUIRE_BASH32:-}" ]; then
      echo "✗ ship push gate, real git: S10 (e) did not run (SHIP_TEST_REQUIRE_BASH32 is set)."; fail=1
    fi
  }
  if ! command -v git >/dev/null 2>&1; then skip_all "no git here"; return 0; fi
  # Windows' Git Bash: git records a worktree's path in its own C:/… form, and its ps reads
  # neither start times nor parent ids, so these cases, written for macOS and Linux, would fail
  # there for reasons of their own. Not run, and said.
  case "$(uname -s 2>/dev/null)" in MINGW*|MSYS*|CYGWIN*) skip_all "Windows (Git Bash)"; return 0 ;; esac
  # ship.sh's worktree mode needs `git worktree remove` (git 2.17).
  gv="$(git version 2>/dev/null | sed -n 's/^git version \([0-9]*\)\.\([0-9]*\).*/\1 \2/p')"
  set -- $gv
  if [ "$#" != 2 ] || [ "$1" -lt 2 ] || { [ "$1" = 2 ] && [ "$2" -lt 17 ]; }; then
    skip_all "it needs git 2.17 or newer ($(git version 2>/dev/null))"; return 0
  fi
  REAL_SLEEP="$(command -v sleep)"; NODE="$(command -v node || true)"; PERL="$(command -v perl || true)"
  # Whether ps here gives start times: without them a lock's owner cannot be told apart from a
  # process that reused its id, so ship.sh says it cannot tell, and S8 and S9 expect that.
  if [ -n "$(ps -o lstart= -p "$$" 2>/dev/null)" ]; then ps_starts=1; else ps_starts=0; fi
  # Real paths (macOS's temp folder is a link), the form git records a worktree's path in.
  G="$(CDPATH= cd -- "$work" && pwd -P)/git"
  mkdir -p "$G/bin" "$G/mk" "$G/home"
  # The repository variables a git hook hands its steps: this file runs inside the pre-push
  # gate, from a linked worktree with GIT_DIR set, and they would aim every git below at it.
  unset $(git rev-parse --local-env-vars)
  # Not this machine's own git settings: no global or system config, an identity of its own.
  export HOME="$G/home" GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null \
    GIT_AUTHOR_NAME=ship-test GIT_AUTHOR_EMAIL=ship-test@example.invalid \
    GIT_COMMITTER_NAME=ship-test GIT_COMMITTER_EMAIL=ship-test@example.invalid \
    SHIP_T_REAL_SLEEP="$REAL_SLEEP" SHIP_T_NODE="$NODE"
  unset XDG_CONFIG_HOME

  # Stub npm. `npm ci` runs the package's prepare step, the real scripts/wire-hooks.mjs, as npm
  # does, so a case sees what an install writes to the clone's shared hooks setting.
  cat > "$G/bin/npm" <<'NPM'
#!/bin/sh
echo "npm $*" >> "$SHIP_T_MARKS/npm-calls"
if [ "${SHIP_T_NPM_FAIL:-}" = 1 ]; then echo "npm ERR! stub: the install failed" >&2; exit 1; fi
if [ "$1" = ci ] && [ -n "${SHIP_T_NODE:-}" ] && [ -f scripts/wire-hooks.mjs ]; then
  echo "prepare: node scripts/wire-hooks.mjs" >> "$SHIP_T_MARKS/npm-calls"
  "$SHIP_T_NODE" scripts/wire-hooks.mjs
fi
exit 0
NPM
  # Stub curl: the live site serves whatever GitHub's production is, as if Cloudflare built it
  # at once; or an old build, for the case stopped during the live check.
  cat > "$G/bin/curl" <<'CURL'
#!/bin/sh
: > "$SHIP_T_MARKS/curl"
if [ -n "${SHIP_T_STALE:-}" ]; then echo 0000000000000000000000000000000000000000; exit 0; fi
git --git-dir="$SHIP_T_ORIGIN" rev-parse refs/heads/production
CURL
  # Stub sleep: no waiting, unless a case needs the live check to be waiting when it signals.
  cat > "$G/bin/sleep" <<'SLEEP'
#!/bin/sh
if [ -n "${SHIP_T_SLEEP:-}" ]; then "$SHIP_T_REAL_SLEEP" "$SHIP_T_SLEEP"; fi
exit 0
SLEEP
  # Stub mktemp, on PATH only for S15 and S17: logs each call's template, fails the one whose
  # template names $SHIP_T_MKTEMP_FAIL, and hands back a folder for the one naming
  # $SHIP_T_MKTEMP_DIR, so a status file written there fails as on a full disk.
  cat > "$G/mk/mktemp" <<MKTEMP
#!/bin/sh
for a in "\$@"; do last="\$a"; done
echo "\$last" >> "\$SHIP_T_MARKS/mktemp-calls"
case "\$last" in *"\${SHIP_T_MKTEMP_FAIL:-//none//}"*) echo "mktemp: stub: this call fails" >&2; exit 1 ;; esac
case "\$last" in *"\${SHIP_T_MKTEMP_DIR:-//none//}"*) "$(command -v mktemp)" -d "\$last"; exit \$? ;; esac
"$(command -v mktemp)" "\$@"
MKTEMP
  chmod +x "$G/bin/npm" "$G/bin/curl" "$G/bin/sleep" "$G/mk/mktemp"

  # The tiny gate: the site's committed scripts/hooks/pre-push in these cases.
  cat > "$G/gate" <<'GATE'
#!/bin/sh
unset $(git rev-parse --local-env-vars)
[ -n "${SHIP_T_SILENT:-}" ] || echo "▶ pre-push gate: tiny gate…"
cat tests/gate.txt
if [ -n "${SHIP_T_GATE_NPM:-}" ]; then npm ci || exit 1; fi
if [ -n "${SHIP_T_RECORD:-}" ]; then git config --get core.hooksPath > "$SHIP_T_RECORD" || echo unset > "$SHIP_T_RECORD"; fi
if [ -n "${SHIP_T_SET_HOOKS:-}" ]; then git config core.hooksPath "$SHIP_T_SET_HOOKS"; fi
if [ -n "${SHIP_T_HOLD:-}" ]; then
  : > "$SHIP_T_MARKS/in-gate"
  i=0
  while [ ! -e "$SHIP_T_MARKS/release" ]; do
    i=$((i + 1)); [ "$i" -gt 1200 ] && { echo "tiny gate: never released" >&2; exit 9; }
    "$SHIP_T_REAL_SLEEP" 0.1
  done
fi
if [ -n "${SHIP_T_MOVE:-}" ]; then git -C "$SHIP_T_MOVE" push -q origin HEAD:refs/heads/production; fi
if [ -e BROKEN ] || [ -e "$SHIP_T_MARKS/fail" ]; then echo "✘ tests: a page is broken"; exit 1; fi
[ -n "${SHIP_T_SILENT:-}" ] || echo "✓ pre-push gate passed — pushing."
GATE

  local D O C S M L rc brc bg before m p0 WT_COUNT LIST_WANT LOCK_LEFT TMP_WT EXTRA_PATH logged
  # Global: the EXIT trap reads them after this function has returned.
  groups="" cname="" rg_done=0
  # fixture <name>: origin with main and production at one commit, the seed, and the clone
  # with the setting on and its hooks setting as the template's install leaves it.
  fixture() {
    D="$G/$1"; O="$D/origin.git"; C="$D/clone"; S="$D/seed"; M="$D/marks"
    mkdir -p "$D/tmp" "$M"
    # Branches named main without `git init -b` (git 2.28), so an older git still runs these.
    git init -q --bare "$O" && git --git-dir="$O" symbolic-ref HEAD refs/heads/main
    git init -q "$S" && git -C "$S" symbolic-ref HEAD refs/heads/main
    mkdir -p "$S/scripts/hooks" "$S/tests"
    cp "$ship" "$S/scripts/ship.sh"
    cp scripts/wire-hooks.mjs "$S/scripts/wire-hooks.mjs"
    cp "$G/gate" "$S/scripts/hooks/pre-push"; chmod +x "$S/scripts/hooks/pre-push"
    printf "export default { site: 'https://ship-test.example.invalid' };\n" > "$S/astro.config.mjs"
    echo "gate input: committed" > "$S/tests/gate.txt"
    echo "a page" > "$S/page.txt"
    echo "keep" > "$S/sentinel.txt"
    git -C "$S" add -A && git -C "$S" commit -qm site
    git -C "$S" remote add origin "$O"
    git -C "$S" push -q origin main main:production
    git clone -q "$O" "$C"
    git -C "$C" config ship.fromGitHub true
    git -C "$C" config core.hooksPath scripts/hooks
    export SHIP_T_ORIGIN="$O" SHIP_T_MARKS="$M" TMPDIR="$D/tmp"
    WT_COUNT=1 LIST_WANT="" LOCK_LEFT=0 TMP_WT=0 EXTRA_PATH=""
  }
  advance() { # <n> commits on GitHub's main, from the seed; production stays where it is
    local i
    for i in $(seq 1 "$1"); do echo "change $i" >> "$S/page.txt"; git -C "$S" commit -qam "change $i"; done
    git -C "$S" push -q origin main
  }
  gh() { git --git-dir="$O" rev-parse "refs/heads/$1"; }
  snap() { # this folder's branch, status and index, read without touching them
    printf '%s|%s|%s' "$(git -C "$C" rev-parse --abbrev-ref HEAD)" \
      "$(git -C "$C" --no-optional-locks status --porcelain)" "$(cksum < "$C/.git/index")"
  }
  worktrees() { git -C "$C" worktree list --porcelain | grep -c '^worktree ' || true; }
  tmp_worktrees() { local n=0 f; for f in "$D/tmp"/ship-worktree.*; do [ -e "$f" ] && n=$((n + 1)); done; echo "$n"; }
  list_now() { cat "$C/.git/ship-worktrees" 2>/dev/null || true; }
  has() { grep -qF -- "$1" "$L"; }
  lacks() { ! grep -qF -- "$1" "$L"; }
  eq() { [ "$1" = "$2" ]; }
  first_line() { awk 'NF { print; exit }' "$L"; }
  last_line() { awk 'NF { l = $0 } END { print l }' "$L"; }
  first_has() { case "$(first_line)" in *"$1"*) return 0 ;; esac; return 1; }
  last_has() { case "$(last_line)" in *"$1"*) return 0 ;; esac; return 1; }
  leaves_nothing() { # no lock, no worktree and no line of its own left, unless the case expects one
    if [ "$LOCK_LEFT" = 0 ]; then [ ! -e "$C/.git/ship.lock" ] || return 1; fi
    [ "$(list_now)" = "$LIST_WANT" ] && [ "$(worktrees)" = "$WT_COUNT" ] && [ "$(tmp_worktrees)" = "$TMP_WT" ]
  }
  want() { # want <what> <test…>: one check of the current case, its run's log shown once on a failure
    rg_n=$((rg_n + 1))
    if ! "${@:2}"; then
      echo "✗ ship push gate, real git [$cname]: $1"
      if [ "$logged" = 0 ] && [ -f "$L" ]; then sed 's/^/  | /' "$L"; logged=1; fi
      fail=1
    fi
  }
  run_ship() { # run_ship <case> [VAR=value…]: the clone's ship.sh, from the clone, as `npm run ship` starts it
    cname="$1"; L="$G/$1.log"; logged=0; shift
    before="$(snap)"; rc=0
    ( CDPATH= cd -- "$C" && env PATH="${EXTRA_PATH:+$EXTRA_PATH:}$G/bin:$PATH" "$@" bash scripts/ship.sh ) > "$L" 2>&1 || rc=$?
    want "this folder's branch, status and index are unchanged" eq "$before" "$(snap)"
    want "no lock, worktree or line of its own left behind" leaves_nothing
  }
  exits() { if [ "$1" = 0 ]; then want "exits 0 (got $rc)" eq "$rc" 0; else want "exits non-zero" test "$rc" != 0; fi; }
  wait_for() { # <file>: with the real sleep and a limit, so a broken case fails instead of hanging
    local i=0
    while [ ! -e "$1" ]; do i=$((i + 1)); [ "$i" -gt 1200 ] && return 1; "$REAL_SLEEP" 0.1; done
  }
  # start_bg <case> <bash> [VAR=value…]: ship.sh in the background, in a process group of its
  # own, so a signal sent to that group can never reach a real publish this file runs inside.
  # perl puts interrupt and quit back to their defaults (a background job of a script starts
  # with them ignored, and bash cannot trap a signal that was ignored when it started), makes
  # the group (macOS has no setsid), then becomes bash; env and perl replace themselves, so $!
  # is the bash that runs ship.sh.
  start_bg() {
    cname="$1"; L="$G/$1.log"; logged=0; local sh="$2"; shift 2
    SHIP_T_DIR="$C" env PATH="$G/bin:$PATH" "$@" perl -e '
      $SIG{INT} = "DEFAULT"; $SIG{QUIT} = "DEFAULT";
      chdir $ENV{SHIP_T_DIR} or die "chdir: $!\n";
      setpgrp(0, 0) or die "setpgrp: $!\n";
      exec { $ARGV[0] } @ARGV or die "exec: $!\n";' "$sh" scripts/ship.sh > "$L" 2>&1 &
    bg=$!; groups="$groups $bg"
  }
  own_group() { # is the run its own process group's leader, in a group that is not this test's?
    local pg mine
    pg="$(ps -o pgid= -p "$bg" 2>/dev/null | tr -d ' ')"; mine="$(ps -o pgid= -p "$$" | tr -d ' ')"
    [ -n "$pg" ] && [ "$pg" = "$bg" ] && [ "$pg" != "$mine" ]
  }
  wait_bg() { # the run's exit status in brc; a run still going after two minutes is killed
    local dog
    perl -e 'sleep 120; kill "KILL", -$ARGV[0]' "$bg" & dog=$!
    brc=0; wait "$bg" || brc=$?
    kill "$dog" 2>/dev/null || true; wait "$dog" 2>/dev/null || true
    # Gone, so off the list the way out kills: a later process could reuse the id.
    local g kept=""; for g in $groups; do [ "$g" = "$bg" ] || kept="$kept $g"; done; groups="$kept"
  }
  # On this file's way out, every group it started goes too. A setup step that fails stops the
  # file (set -e) with no word of its own, so say which case it was in.
  trap 'for g in $groups; do kill -KILL -- "-$g" 2>/dev/null || true; done
    if [ "$rg_done" != 1 ]; then echo "✗ ship push gate, real git: stopped part-way, in or after case [$cname]; the cases after it did not run."; fi
    rm -rf "$work"' EXIT

  # --- S2: a feature branch, an edit and an untracked folder; GitHub's main two ahead -------
  fixture s2; advance 2
  git -C "$C" checkout -q -b feat
  echo "an edit" >> "$C/page.txt"
  mkdir "$C/data" && echo "1,2" > "$C/data/x.csv"
  # A tracked file's time changed but not its content: plain `git status` would now rewrite
  # the index, so the index check below can fail.
  touch -t 202001010000 "$C/astro.config.mjs"
  m="$(gh main)"
  run_ship s2; exits 0
  want "production is GitHub's main" eq "$(gh production)" "$m"
  want "the first line names the mode and the commit" first_has "Publishing GitHub's main as of the fetch (${m:0:12})"
  want "the edited file is listed as not published" has "     M page.txt"
  want "the untracked folder is listed as not published" has "    ?? data/"
  want "the last line is the LIVE line with the count" last_has "2 not published"
  want "... and starts with ✓ LIVE" eval 'case "$(last_line)" in "✓ LIVE"*) true ;; *) false ;; esac'
  want "no message claims this folder is on main" lacks "safely on 'main'"
  want "the folder is still on its branch" eq "$(git -C "$C" rev-parse --abbrev-ref HEAD)" feat

  # --- S3: this computer's main one commit ahead of GitHub's ------------------------------
  fixture s3; advance 1
  git -C "$C" pull -q --ff-only
  echo "local" >> "$C/page.txt"; git -C "$C" commit -qam "not on GitHub"
  m="$(gh main)"
  run_ship s3; exits 0
  want "production is GitHub's main, not this computer's" eq "$(gh production)" "$m"
  want "says the commit was not published" has "this computer's 'main' has 1 commit that GitHub's main doesn't"

  # --- S4: GitHub's main has a broken page ------------------------------------------------
  fixture s4
  echo "broken" > "$S/BROKEN"; git -C "$S" add BROKEN; git -C "$S" commit -qm "a broken page"; git -C "$S" push -q origin main
  m="$(gh main)"
  p0="$(gh production)"
  run_ship s4; exits 1
  want "production is unchanged" eq "$(gh production)" "$p0"
  want "the tests failed inside the worktree" has "✘ tests: a page is broken"
  want "nothing was published, this folder untouched" has "Nothing was published and this folder was not touched."
  want "the last line names the commit it was for" last_has "GitHub's main as of the fetch: ${m:0:12}"

  # --- S6: the package install fails ------------------------------------------------------
  fixture s6; advance 1; p0="$(gh production)"
  run_ship s6 SHIP_T_NPM_FAIL=1; exits 1
  want "production is unchanged" eq "$(gh production)" "$p0"
  want "says the install failed" has "installing the site's packages in the temporary copy failed"
  want "stops before the push" lacks "▶ pre-push gate"

  # --- S7: another clone moves production while the gate runs -----------------------------
  fixture s7; advance 1
  git clone -q "$O" "$D/clone2"
  git -C "$D/clone2" checkout -q -b moved origin/production
  git -C "$D/clone2" commit -q --allow-empty -m "published from elsewhere"
  m="$(git -C "$D/clone2" rev-parse HEAD)"
  run_ship s7 SHIP_T_MOVE="$D/clone2"; exits 1
  want "production is the other clone's" eq "$(gh production)" "$m"
  want "git's own refusal reached the log" eval 'grep -qE "^ *! \[remote rejected\] .*\((failed to update ref|incorrect old value provided)\)" "$L"'
  want "names it as production moved" has "moved while this was publishing"

  # --- S8: an earlier run killed hard: its lock and worktrees left -------------------------
  fixture s8; advance 1; p0="$(gh production)"
  local l1="$D/tmp/ship-worktree.left1" l2="$D/tmp/ship-worktree.left2" gone="$D/tmp/ship-worktree.gone"
  git -C "$C" worktree add -q --detach "$l1"; echo "work in progress" > "$l1/note.txt"
  git -C "$C" worktree add -q --detach "$l2"; rm -rf "$l2"
  # The third line's worktree was removed by hand since: neither its folder nor git's record is left.
  # The fourth was cut short (a full disk) and names the folder above; the fifth was cut short
  # inside a name this script gives (its tab and the fields after it lost). Neither gets a delete
  # command.
  mkdir "$D/tmp/ship-worktree.trunc"
  printf '%s\t4242\tThu Jan  1 00:00:00 1970\n%s\t4243\tThu Jan  1 00:00:00 1970\n%s\t4244\tThu Jan  1 00:00:00 1970\n%s\t4245\tThu Jan  1 00:00:00 1970\n%s\n' \
    "$l1" "$l2" "$gone" "$D/tmp" "$D/tmp/ship-worktree.trunc" > "$C/.git/ship-worktrees"
  # A lock naming a running process (this test), on this computer, with another start time: the
  # process id was reused.
  mkdir "$C/.git/ship.lock"; echo "$$" > "$C/.git/ship.lock/pid"; echo "Thu Jan  1 00:00:00 1970" > "$C/.git/ship.lock/start"
  uname -n > "$C/.git/ship.lock/host"
  WT_COUNT=3 TMP_WT=2 LOCK_LEFT=1 LIST_WANT="$(list_now)"
  run_ship s8-lock; exits 1
  want "production is unchanged" eq "$(gh production)" "$p0"
  want "names the lock by its full path" has "    $C/.git/ship.lock"
  if [ "$ps_starts" = 1 ]; then
    want "says its process is not running" has "That process is not running"
  else
    want "says it cannot tell (ps gives no start times here)" has "cannot tell whether that publish is still running"
  fi
  want "warns that a killed run's push may still be running" has "can leave its push and its tests running"
  want "gives the command that removes the lock" has "    rm -r '$C/.git/ship.lock'"
  want "the lock is still there, naming the same process" eq "$(cat "$C/.git/ship.lock/pid")" "$$"
  # The command it printed, run as the person would.
  eval "$(sed -n "s/^    \(rm -r '.*'\)\$/\1/p" "$L")" 2>/dev/null || true
  want "the printed command removed the lock" test ! -e "$C/.git/ship.lock"
  rm -rf "$C/.git/ship.lock"; mkdir "$C/.git/ship.lock"   # a lock with no process id yet
  run_ship s8-nopid; exits 1
  want "without a process id it says it cannot tell" has "cannot tell whether that publish is still running"
  want "... with the warning and the command" has "    rm -r '$C/.git/ship.lock'"
  eval "$(sed -n "s/^    \(rm -r '.*'\)\$/\1/p" "$L")" 2>/dev/null || true
  # Written on another computer (a shared disk), with a start time that does not match here:
  # not "gone" from here, but no telling.
  rm -rf "$C/.git/ship.lock"; mkdir "$C/.git/ship.lock"
  echo "$$" > "$C/.git/ship.lock/pid"; echo "Thu Jan  1 00:00:00 1970" > "$C/.git/ship.lock/start"; echo another-computer > "$C/.git/ship.lock/host"
  run_ship s8-otherhost; exits 1
  want "a lock from another computer is \"cannot tell\", not \"not running\"" has "cannot tell whether that publish is still running"
  if [ "$ps_starts" = 1 ]; then
    # A matching process id and start time is a running publish, whatever the computer's name
    # says now: a Mac's name can change with the network.
    LC_ALL=C TZ=UTC ps -o lstart= -p "$$" | sed -e 's/^ *//' -e 's/ *$//' > "$C/.git/ship.lock/start"
    run_ship s8-renamed; exits 1
    want "a running match is \"under way\", whatever the host name" has "a publish is under way"
  fi
  rm -rf "$C/.git/ship.lock"
  LOCK_LEFT=0 LIST_WANT="$(printf '%s\t4242\tThu Jan  1 00:00:00 1970\n%s\t4243\tThu Jan  1 00:00:00 1970\n%s\t4245\tThu Jan  1 00:00:00 1970\n%s' "$l1" "$l2" "$D/tmp" "$D/tmp/ship-worktree.trunc")"
  m="$(gh main)"
  run_ship s8-next; exits 0
  want "publishes" eq "$(gh production)" "$m"
  want "reports the leftover with its folder" has "    $l1  (made by process 4242"
  want "... and its removal command" has "git worktree remove --force --force '$l1'"
  want "reports the leftover whose folder is gone" has "git worktree remove --force --force '$l2'"
  want "does not report the one removed by hand" lacks "$gone"
  want "gives no delete command for a folder this script does not name" lacks "rm -rf '$D/tmp'"
  want "... nor for a ship-worktree line cut short" lacks "rm -rf '$D/tmp/ship-worktree.trunc'"
  # Each of the two damaged lines gets its own report: its path line, then the by-hand advice;
  # and a line with no fields is not read as a process id.
  want "a line with no fields names no process" lacks "(made by process $D/"
  want "... nor one that is not a whole line this script wrote" lacks "(made by process 4245"
  local damaged
  for damaged in "$D/tmp" "$D/tmp/ship-worktree.trunc"; do
    want "reports $damaged, then says to check it by hand, naming the list" \
      eval 'awk -v p="    $damaged" -v h="      remove with:  (check it by hand: not a whole line this script wrote; then delete the line from $C/.git/ship-worktrees)" \
        "f { ok = (\$0 == h); f = 0; seen = 1 } \$0 == p || index(\$0, p \"  (\") == 1 { f = 1 } END { exit !(seen && ok) }" "$L"'
  done
  want "the leftover's files are untouched" eq "$(cat "$l1/note.txt")" "work in progress"

  # --- S9: a publish already running in this clone ----------------------------------------
  # The second run asks in another time zone and language, as an assistant started from an app
  # may, while the first runs in a terminal: ps writes start times in the caller's.
  if [ -z "$PERL" ]; then
    rg_skipped="${rg_skipped:+$rg_skipped; }S9 skipped: no perl here"
    echo "  note: S9 (a publish already running) is skipped: it starts the first run with perl, which is not here."
  else
    fixture s9; advance 1; m="$(gh main)"
    local first_pid first_start first_log first
    start_bg s9-first bash SHIP_T_HOLD=1; first_log="$L"; first="$bg"
    if wait_for "$M/in-gate"; then
      first_pid="$(cat "$C/.git/ship.lock/pid" 2>/dev/null)" || true; first_start="$(cat "$C/.git/ship.lock/start" 2>/dev/null)" || true
      WT_COUNT=2 TMP_WT=1 LOCK_LEFT=1 LIST_WANT="$(list_now)"
      run_ship s9-second TZ=Asia/Tokyo LANG=de_DE.UTF-8 LC_TIME=de_DE.UTF-8; exits 1
      if [ "$ps_starts" = 1 ]; then
        want "says a publish is under way" has "a publish is under way"
        want "gives no removal command" lacks "rm -r"
      else
        want "says it cannot tell (ps gives no start times here)" has "cannot tell whether that publish is still running"
      fi
      want "the lock still names the first run" eq "$(cat "$C/.git/ship.lock/pid") $(cat "$C/.git/ship.lock/start")" "$first_pid $first_start"
      want "the first run is still running" kill -0 "$first"
    else
      cname=s9; want "the first run reached its gate" false
    fi
    : > "$M/release"; bg="$first"; wait_bg
    cname=s9-first; L="$first_log"; logged=0; WT_COUNT=1 TMP_WT=0 LOCK_LEFT=0 LIST_WANT=""
    want "the first run publishes" eq "$brc $(gh production)" "0 $m"
    want "... and leaves nothing behind" leaves_nothing
  fi

  # --- S10: stops (Ctrl-C to the whole group, or a terminate to the script alone) ----------
  if [ -z "$PERL" ]; then
    rg_skipped="${rg_skipped:+$rg_skipped; }S10 skipped: no perl here"
    echo "  note: S10 (stopping a publish) is skipped: it starts each run with perl, which is not here."
    if [ -n "${SHIP_TEST_REQUIRE_BASH32:-}" ]; then
      cname=s10e; want "S10 (e) ran (SHIP_TEST_REQUIRE_BASH32 is set)" false
    fi
  else
    # signal_case <case> <bash> <marker to wait for> <group-int|script-term> <release|-> [VAR=value…]
    signal_case() {
      local name="$1" sh="$2" marker="$3" how="$4" after="$5"; shift 5
      start_bg "$name" "$sh" "$@"
      if ! wait_for "$M/$marker"; then
        want "reached the point where it is stopped" false; : > "$M/release"
      elif ! own_group; then
        want "runs in a process group of its own before it is signalled" false; : > "$M/release"
      else
        case "$how" in group-int) kill -INT -- "-$bg" ;; script-term) kill -TERM "$bg" ;; esac
        if [ "$after" = release ]; then : > "$M/release"; fi
      fi
      wait_bg; rc="$brc"
      want "exits non-zero" test "$rc" != 0
      want "no lock, worktree or line of its own left behind" leaves_nothing
    }
    fixture s10a; advance 1; p0="$(gh production)"
    signal_case s10a bash in-gate group-int - SHIP_T_HOLD=1
    want "says it was stopped" has "Publish stopped"
    want "may or may not have landed" has "may or may not have landed"
    want "says to run it again" has "npm run ship"
    want "production is unchanged" eq "$(gh production)" "$p0"

    fixture s10b; advance 1; m="$(gh main)"
    signal_case s10b bash in-gate script-term release SHIP_T_HOLD=1
    want "says a stop was asked for" has "a stop was asked for"
    want "says the publish went out" has "The publish went out"
    want "says the live check was skipped" has "The live-site check was skipped"
    want "production is GitHub's main" eq "$(gh production)" "$m"

    fixture s10c; advance 1; p0="$(gh production)"
    signal_case s10c bash in-gate group-int - SHIP_T_HOLD=1 SHIP_T_SILENT=1
    want "may or may not have landed" has "may or may not have landed"
    want "production is unchanged" eq "$(gh production)" "$p0"

    fixture s10d; advance 1; m="$(gh main)"
    signal_case s10d bash in-gate script-term release SHIP_T_HOLD=1 SHIP_T_SILENT=1
    want "says the publish went out" has "The publish went out"
    want "says the live check was skipped" has "The live-site check was skipped"
    want "production is GitHub's main" eq "$(gh production)" "$m"

    # (e) the Mac's own bash 3.2, where a stop noted as the push pipeline ends resets that
    # pipeline's per-command status: read from there, git's failure would read as a success.
    if [ "$(/bin/bash -c 'echo "${BASH_VERSINFO[0]}.${BASH_VERSINFO[1]}"' 2>/dev/null)" = 3.2 ]; then
      fixture s10e; advance 1; p0="$(gh production)"
      start_bg s10e /bin/bash SHIP_T_HOLD=1
      if wait_for "$M/in-gate" && own_group && [ "$(ps -o comm= -p "$bg")" = /bin/bash ]; then
        kill -TERM "$bg"; : > "$M/fail"; : > "$M/release"
      else
        want "runs as /bin/bash 3.2, in a group of its own, at its gate" false; : > "$M/release"
      fi
      wait_bg; rc="$brc"
      want "exits non-zero" test "$rc" != 0
      want "the failed push is not reported as a success" lacks "The publish went out"
      want "may or may not have landed" has "may or may not have landed"
      want "production is unchanged" eq "$(gh production)" "$p0"
      want "no lock, worktree or line of its own left behind" leaves_nothing
    else
      rg_skipped="${rg_skipped:+$rg_skipped; }S10 (e) skipped: /bin/bash here is not bash 3.2"
      echo "  note: S10 (e) skipped: it needs the Mac's own bash 3.2 as /bin/bash."
      if [ -n "${SHIP_TEST_REQUIRE_BASH32:-}" ]; then
        cname=s10e; want "S10 (e) ran (SHIP_TEST_REQUIRE_BASH32 is set)" false
      fi
    fi

    fixture s10f; advance 1; m="$(gh main)"
    signal_case s10f bash curl group-int - SHIP_T_STALE=1 SHIP_T_SLEEP=1
    want "says the live check was stopped" has "Stopped during the live-site check"
    want "says the publish went out" has "The publish went out"
    want "production is GitHub's main" eq "$(gh production)" "$m"
  fi

  # --- S11: this folder's hook and tests edited, not committed -----------------------------
  fixture s11; advance 1; m="$(gh main)"
  printf '#!/bin/sh\necho "FOLDER HOOK RAN"\nexit 1\n' > "$C/scripts/hooks/pre-push"
  echo "gate input: folder" > "$C/tests/gate.txt"
  run_ship s11; exits 0
  want "production is GitHub's main" eq "$(gh production)" "$m"
  want "the gate read the committed tests" has "gate input: committed"
  want "... not this folder's" lacks "gate input: folder"
  want "this folder's hook did not run" lacks "FOLDER HOOK RAN"

  # --- S13: GitHub's main already equals production ----------------------------------------
  fixture s13
  run_ship s13; exits 0
  want "git says it is up to date" has "Everything up-to-date"
  want "the live check passes" has "✓ LIVE"

  # --- S14: another session's worktree, its folder moved away; housekeeping due ------------
  # With the fetch's housekeeping on, git would prune its record: the only record of commits
  # made there.
  fixture s14; advance 1
  git -C "$C" worktree add -q --detach "$D/other"; mv "$D/other" "$D/other-away"
  git -C "$C" config gc.auto 1; git -C "$C" config gc.autoDetach false
  git -C "$C" config gc.worktreePruneExpire now
  # Housekeeping is due once more than one loose object sits in objects/17 (gc.auto 1 / 256).
  local batch=0 i
  mkdir -p "$D/blobs"
  while [ "$(find "$C/.git/objects/17" -type f 2>/dev/null | wc -l | tr -d ' ')" -lt 2 ]; do
    batch=$((batch + 1)); [ "$batch" -gt 20 ] && break
    for i in $(seq 1 200); do echo "loose $batch $i" > "$D/blobs/$batch-$i"; done
    (CDPATH= cd -- "$D/blobs" && ls | git --git-dir="$C/.git" hash-object -w --stdin-paths --no-filters >/dev/null)
  done
  WT_COUNT=2
  run_ship s14; exits 0
  want "the moved-away worktree is still registered" grep -qxF "worktree $D/other" <<<"$(git -C "$C" worktree list --porcelain)"
  # The control: in the same clone, one plain fetch with its housekeeping on drops that record.
  # Without it, the check above could pass because housekeeping would not have pruned anyway.
  advance 1; git -C "$C" fetch -q origin 2>>"$L" || true
  want "control: a plain fetch with housekeeping on drops the record (so the check above can fail)" \
    eval '! grep -qxF "worktree $D/other" <<<"$(git -C "$C" worktree list --porcelain)"'

  # --- S15: one mktemp call fails, each in turn -------------------------------------------
  fixture s15; advance 1; p0="$(gh production)"
  EXTRA_PATH="$G/mk"; : > "$M/mktemp-calls"
  run_ship s15-count; exits 0
  local calls name sum
  calls="$(sed 's/.*\///; s/\..*//' "$M/mktemp-calls" | sort -u)"
  want "makes its log, status file and worktree with mktemp" eq "$(echo $calls)" "ship-log ship-status ship-worktree"
  git --git-dir="$O" update-ref refs/heads/production "$p0"
  sum="$(cksum < "$C/sentinel.txt")"
  for name in $calls; do
    run_ship "s15-$name" SHIP_T_MKTEMP_FAIL="$name."; exits 1
    want "production is unchanged" eq "$(gh production)" "$p0"
    want "the committed sentinel is unchanged" eq "$(cksum < "$C/sentinel.txt")" "$sum"
    want "the error is the last line" last_has "couldn't create a temporary file or folder"
  done

  # --- S16: this folder's ship.sh is not GitHub's ------------------------------------------
  fixture s16; advance 1; p0="$(gh production)"
  echo "# an edit nobody committed" >> "$C/scripts/ship.sh"
  run_ship s16-edit; exits 1
  want "production is unchanged" eq "$(gh production)" "$p0"
  want "says the two files differ though the versions match" has "Both say template-version $ship_version, but the two files differ anyway"
  git -C "$C" checkout -q -- scripts/ship.sh
  git -C "$C" checkout -q -b old
  sed "s/^# template-version: $ship_version/# template-version: 0.21/" "$C/scripts/ship.sh" > "$D/old.sh"
  cat "$D/old.sh" > "$C/scripts/ship.sh"; git -C "$C" commit -qam "an older ship.sh"
  run_ship s16-old; exits 1
  want "production is unchanged" eq "$(gh production)" "$p0"
  want "names both versions" has "This folder's copy says template-version 0.21; GitHub's main as of the"
  want "... GitHub's too" has "has $ship_version."

  # --- S17: the push goes out, but its status file cannot be written ----------------------
  fixture s17; advance 1; m="$(gh main)"
  EXTRA_PATH="$G/mk"
  run_ship s17 SHIP_T_MKTEMP_DIR=ship-status.; exits 1
  want "the push went out" eq "$(gh production)" "$m"
  want "may or may not have landed" has "may or may not have landed"
  want "never says nothing was published" lacks "Nothing was published"
  want "never says LIVE" lacks "✓ LIVE"

  # --- S18: the clone's shared hooks setting elsewhere, unset, changed; no hook ------------
  fixture s18; advance 1
  mkdir -p "$D/elsewhere"; printf '#!/bin/sh\necho "ELSEWHERE HOOK RAN"\nexit 1\n' > "$D/elsewhere/pre-push"; chmod +x "$D/elsewhere/pre-push"
  # ...and hooks there that making a worktree would start (its checkout runs post-checkout and
  # post-index-change); one that installed packages would rewrite the shared hooks setting
  # mid-publish.
  for h in post-checkout post-index-change; do
    printf '#!/bin/sh\necho %s >> "%s/foreign-hooks-ran"\n' "$h" "$M" > "$D/elsewhere/$h"; chmod +x "$D/elsewhere/$h"
  done
  # reference-transaction runs for the fetch too, but only making a worktree touches HEAD.
  printf '#!/bin/sh\nwhile read -r _o _n ref; do echo "$ref" >> "%s/foreign-reftx"; done\n' "$M" > "$D/elsewhere/reference-transaction"
  chmod +x "$D/elsewhere/reference-transaction"
  # ...and the same hooks committed in a folder named like a pin inside the checkout would be: a
  # pin there would run them once the checkout wrote them.
  mkdir -p "$S/.ship-no-hooks"
  for h in post-checkout post-index-change; do
    printf '#!/bin/sh\necho %s >> "%s/committed-hooks-ran"\n' "$h" "$M" > "$S/.ship-no-hooks/$h"; chmod +x "$S/.ship-no-hooks/$h"
  done
  git -C "$S" add .ship-no-hooks; git -C "$S" commit -qm "a folder of hooks"; git -C "$S" push -q origin main
  git -C "$C" config core.hooksPath "$D/elsewhere"
  run_ship s18-elsewhere; exits 0
  want "the commit's own gate ran" has "▶ pre-push gate: tiny gate"
  want "... not the one the shared setting names" lacks "ELSEWHERE HOOK RAN"
  want "making the worktree started none of the shared folder's hooks" test ! -e "$M/foreign-hooks-ran"
  want "... nor its reference-transaction hook for the worktree's HEAD" eval '! grep -qxE "(ORIG_)?HEAD" "$M/foreign-reftx" 2>/dev/null'
  want "... nor hooks committed in the checkout" test ! -e "$M/committed-hooks-ran"
  want "the shared setting is as it was" eq "$(git -C "$C" config --get core.hooksPath)" "$D/elsewhere"
  advance 1; git -C "$C" config --unset core.hooksPath
  run_ship s18-unset; exits 0
  want "the commit's own gate ran with the setting unset" has "▶ pre-push gate: tiny gate"
  want "production is GitHub's main" eq "$(gh production)" "$(gh main)"
  advance 1; git -C "$C" config core.hooksPath scripts/hooks
  run_ship s18-changed SHIP_T_SET_HOOKS="$D/changed"; exits 0
  want "the gate ran though the setting changed during it" has "✓ pre-push gate passed"
  want "the other session's change stays" eq "$(git -C "$C" config --get core.hooksPath)" "$D/changed"
  git -C "$C" config core.hooksPath scripts/hooks
  git -C "$S" rm -q scripts/hooks/pre-push; git -C "$S" commit -qm "no hook"; git -C "$S" push -q origin main
  p0="$(gh production)"
  run_ship s18-nohook; exits 1
  want "says the commit has no runnable hook" has "has no runnable"
  want "production is unchanged" eq "$(gh production)" "$p0"
  # A hook that is there but not runnable: git would skip it with a hint and push anyway.
  mkdir -p "$S/scripts/hooks"; cp "$G/gate" "$S/scripts/hooks/pre-push"; chmod -x "$S/scripts/hooks/pre-push"
  git -C "$S" add scripts/hooks/pre-push; git -C "$S" update-index --chmod=-x scripts/hooks/pre-push
  git -C "$S" commit -qm "a hook that is not runnable"; git -C "$S" push -q origin main
  run_ship s18-noexec; exits 1
  want "says the commit has no runnable hook" has "has no runnable"
  want "production is unchanged" eq "$(gh production)" "$p0"

  # --- S19: a worktree ship did not make, named like ship's, locked, with work in it -------
  fixture s19; advance 1; m="$(gh main)"
  local fw="$D/tmp/ship-worktree.foreign"
  git -C "$C" worktree add -q --detach "$fw"; git -C "$C" worktree lock --reason "another tool's" "$fw"
  echo "draft" > "$fw/draft.txt"; echo "an edit" >> "$fw/page.txt"
  sum="$(cat "$fw/draft.txt" "$fw/page.txt" | cksum)"
  WT_COUNT=2 TMP_WT=1
  run_ship s19; exits 0
  want "publishes" eq "$(gh production)" "$m"
  want "the other worktree is still registered and locked" eq "$(git -C "$C" worktree list --porcelain | awk -v p="worktree $fw" '$0 == p { f = 1; next } /^worktree / { f = 0 } f && /^locked/ { print "locked" }')" locked
  want "... with its files unchanged" eq "$(cat "$fw/draft.txt" "$fw/page.txt" | cksum)" "$sum"
  want "... and is not reported" lacks "$fw"

  # --- S20: the clone's fetch setting narrowed to production; GitHub's main ahead ----------
  fixture s20
  git -C "$C" config remote.origin.fetch '+refs/heads/production:refs/remotes/origin/production'
  advance 1; m="$(gh main)"
  run_ship s20; exits 0
  want "production is GitHub's main as of the fetch" eq "$(gh production)" "$m"
  want "the first line names that commit" first_has "${m:0:12}"
  want "the last line names that commit" last_has "${m:0:12}"

  # --- S21: another session set the clone's hooks setting to its own folder ----------------
  if [ -z "$NODE" ]; then
    rg_skipped="${rg_skipped:+$rg_skipped; }S21 skipped: no node here"
    echo "  note: S21 skipped: it runs scripts/wire-hooks.mjs, which needs node."
  else
    fixture s21; advance 1
    git -C "$C" config core.hooksPath "$D/another-session"
    run_ship s21 SHIP_T_RECORD="$M/recorded" SHIP_T_GATE_NPM=1; exits 0
    want "the gate's own install ran too" eq "$(grep -c '^prepare: ' "$M/npm-calls")" 2
    want "during the push the setting was the other session's" eq "$(cat "$M/recorded")" "$D/another-session"
    want "... and it still is" eq "$(git -C "$C" config --get core.hooksPath)" "$D/another-session"
  fi

  # --- P1–P5: the last line for a pages.dev address and for a real domain, in both modes ---
  # A *.pages.dev address is Cloudflare's own address for the site: the build served there does
  # not show the site is live on its own domain, so the line must not say LIVE; a real domain
  # keeps it. P3 and P4 run with the setting off; P5 writes the host in capitals with a final dot.
  last_starts() { case "$(last_line)" in "$1"*) return 0 ;; esac; return 1; }
  site_case() { # <case> <github|folder> <the site's address>
    fixture "$1"
    printf "export default { site: '%s' };\n" "$3" > "$S/astro.config.mjs"
    git -C "$S" commit -q --allow-empty -am "site address"; git -C "$S" push -q origin main
    git -C "$C" pull -q --ff-only
    if [ "$2" = folder ]; then
      git -C "$C" config --unset ship.fromGitHub
      # Files dated in the past, so ship.sh's own git status finds nothing to rewrite in the index.
      find "$C" -path "$C/.git" -prune -o -type f -exec touch -t 202001010000 {} +
      git -C "$C" update-index -q --refresh
    fi
    m="$(gh main)"
    run_ship "$1"; exits 0
    want "production is GitHub's main" eq "$(gh production)" "$m"
    if [ "$2" = folder ]; then want "publishes this folder's main" first_has "Publishing main → production."; fi
  }
  pv="✓ Published — verified on the pages.dev address: https://ship-test.pages.dev is serving"
  pv_note="That's Cloudflare's address for the site, not your own domain: the site is live on your domain only once that's connected."
  site_case p1 github https://ship-test.pages.dev
  want "the last line names the pages.dev address" last_starts "$pv GitHub's main as of the fetch (${m:0:12})"
  want "... and says it is not the site's own domain" last_has "$pv_note"
  want "never says LIVE" lacks "✓ LIVE"
  site_case p2 github https://ship-test.example.invalid
  want "a real domain keeps the LIVE line" last_starts "✓ LIVE — verified: https://ship-test.example.invalid is serving GitHub's main as of the fetch (${m:0:12})"
  want "... with no pages.dev note" lacks "$pv_note"
  site_case p3 folder https://ship-test.pages.dev
  want "the last line names the pages.dev address" last_starts "$pv build ${m:0:12} (after"
  want "... and says it is not the site's own domain" last_has "$pv_note"
  want "never says LIVE" lacks "✓ LIVE"
  site_case p4 folder https://ship-test.example.invalid
  want "a real domain keeps the LIVE line" last_starts "✓ LIVE — verified: https://ship-test.example.invalid is serving build ${m:0:12} (after"
  want "... with no pages.dev note" lacks "$pv_note"
  site_case p5 github https://Ship-Test.PAGES.DEV.
  want "a host in capitals with a final dot is a pages.dev address too" last_starts "✓ Published — verified on the pages.dev address: https://Ship-Test.PAGES.DEV. is serving"
  want "never says LIVE" lacks "✓ LIVE"
  rg_done=1
}

real_git_cases

if [ "$fail" -eq 0 ]; then
  echo "✓ ship push gate: $checked publish outcomes classified correctly (fetch, ahead/behind, divergence, race, network, mid-transfer drop, red gate, access, stop, clean), and $rg_n checks on real git (the mode that publishes GitHub's main, and the last line for a pages.dev address in both modes)${rg_skipped:+ ($rg_skipped)}${stub_skipped:+; skipped: $stub_skipped}"
fi
exit "$fail"
