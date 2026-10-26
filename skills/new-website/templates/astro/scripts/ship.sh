#!/usr/bin/env bash
# Publish: promote the current preview (`main`) to the live site (`production`).
# Two-stage sites only. Validates BEFORE doing anything so a beginner can't half-publish.
#
# template-version: 0.23
#   The website-builder release this revision ships in. Sites get their copy at
#   scaffold time and then diverge, so this is how you tell whether a site is current:
#   `grep template-version scripts/ship.sh`. Bump it when this file changes, and keep
#   tests/check_ship_push.sh's marker in step — that test asserts the two agree.
#
# Two modes. As shipped, it publishes THIS folder's `main`, and stops unless the folder is on
# `main`, has no unsaved files and matches GitHub's copy. Where several people or AI sessions
# share one checkout, the folder is seldom like that, and files that have nothing to do with
# the publish block it. For such a clone, `git config ship.fromGitHub true` (the clone's own
# config; a global value is ignored, so a fresh clone keeps the check) makes it publish
# GitHub's `main` instead, from a throwaway git worktree made at that exact commit and removed
# on every exit. The pre-push gate then tests exactly the commit that goes live, and nothing
# in this folder is built, tested, published or changed: its unsaved files are only listed.
#
# Two rules hold for the whole file, in both modes:
#  - The body is the function `ship`, called on the last line together with `exit`. bash reads
#    a script as it runs it, so an edit another session saves to this file mid-publish would
#    run; a function is read whole before it starts, and nothing after that line is read.
#  - Nothing here may replace the shell with another program (tests/check_ship_push.sh bans
#    the builtin that does it, outright): the EXIT trap, which removes the worktree and the
#    lock, would never run.

# The fetch below and the push further down have to answer the same question from git's
# own words — "was that the network?" — so it gets ONE definition. Two copies of this
# pattern would drift the first time a newly-seen failure is added to only one of them,
# and the drift would be invisible: both greps still look plausible on their own.
# The mirror of the function below, and just as load-bearing: these all END in
# "fatal: Could not read from remote repository", so without taking them out first the
# network pattern claims them and the owner is told to just run it again. Host-key
# failures are the case that makes this a security matter and not only an annoyance —
# a changed host key can mean a machine-in-the-middle, and "try again" is the worst
# possible advice for it. (Both classifiers pre-filtered, but with DIFFERENT lists,
# until an independent review pointed out the drift the shared function below was
# extracted to prevent.)
looks_like_local_or_auth_failure() { # <git's output, as text>
  # "Permission to <repo> denied to <user>" is GitHub's actual wording and does NOT
  # contain "Permission denied" — it fell through to the network test, matched the
  # generic "Could not read from remote repository" there, and was retried as a blip.
  # Caught by an independent review after this list had been copied into other repos,
  # which is exactly why it is one definition per repo and not one per call site.
  grep -qE 'does not appear to be a git repository|Permission denied|Permission to [^[:space:]]+ denied|Repository not found|could not read Username|Authentication failed|remote: Invalid username or password|Host key verification failed|REMOTE HOST IDENTIFICATION HAS CHANGED' <<<"$1"
}

looks_like_network_failure() { # <git's output, as text>
  grep -qE '^(ssh: connect to host |Connection (closed|reset) by |fatal: Could not read from remote repository)' <<<"$1" \
    || grep -qE '^fatal: unable to access .*(Could not resolve host|Failed to connect|Connection (timed out|refused|reset)|Operation timed out|Recv failure|Send failure|Empty reply)' <<<"$1" \
    || grep -qE '^(error: RPC failed; curl [0-9]+|fatal: early EOF|send-pack: unexpected disconnect|fatal: [Tt]he remote end hung up)' <<<"$1"
}

# The log as every check below reads it: without the lines tests/check_ship_push.sh prints, behind
# "  | ", for one of its own failing cases. That test runs inside the pre-push gate, and its nested
# runs of this script print gate, refusal, login and port lines that are not this publish's.
log_view() { grep -v '^  | ' "$1" 2>/dev/null || true; }

# A process's start time as `ps` gives it, spaces trimmed; empty where ps cannot say (Windows'
# Git Bash has no `-o lstart`) or the process is gone. With the id it tells a running process
# from a later one that reused the id. In one time zone and language whoever asks: ps writes the
# time in the caller's, and two sessions sharing a clone (a terminal, an assistant started from
# an app) need not share either.
proc_start() {
  local s
  s="$(LC_ALL=C TZ=UTC ps -o lstart= -p "$1" 2>/dev/null)" || s=""
  s="${s#"${s%%[![:space:]]*}"}"
  printf '%s' "${s%"${s##*[![:space:]]}"}"
}

# A folder's full path the way git records a worktree's: links resolved (macOS's temp folder is
# /var/…, a link to /private/var/…), and on Windows' Git Bash in git's own C:/… form.
real_dir() {
  ( CDPATH= cd -- "$1" 2>/dev/null || exit 1
    if command -v cygpath >/dev/null 2>&1; then cygpath -m "$(pwd -P)"; else pwd -P; fi )
}

registered() { # <path>: is it one of this clone's worktrees, by git's records?
  local wl
  wl="$(git worktree list --porcelain 2>/dev/null)" || return 1
  grep -qxF "worktree $1" <<<"$wl"
}

stop_point() { # <what is true now, one sentence>: stop here if a stop was asked for
  [ "$stop_asked" = 1 ] || return 0
  stop_said=1
  echo ""
  echo "✗ Publish stopped — a stop was asked for (Ctrl-C, or a terminate signal)."
  echo "  $1"
  exit 1
}

no_temp() { # one line, so it stays the last thing printed
  echo "✗ Publish stopped — couldn't create a temporary file or folder (mktemp failed: a full disk, or TMPDIR naming a folder that is missing?). Nothing was published and $here."
  exit 1
}

# The fetch, with git's automatic housekeeping off for it. Housekeeping can prune, and a prune
# drops the record of another session's worktree whose folder is only away (an unmounted disk,
# say), and with it the only record of commits made there. Two settings rather than the
# --no-auto-maintenance switch: an older git refuses a switch it does not know, and ignores a
# setting. In worktree mode the fetch names its two branches, each forced into its
# remote-tracking ref as git's default fetch setting does, so a narrowed fetch setting in the
# clone's shared config cannot leave origin/main stale. A branch missing on GitHub then fails the
# fetch with git's own words ("couldn't find remote ref refs/heads/production").
fetch_origin() {
  if [ "$from_github" = 1 ]; then
    git -c maintenance.auto=false -c gc.auto=0 fetch -q origin \
      '+refs/heads/main:refs/remotes/origin/main' '+refs/heads/production:refs/remotes/origin/production'
  else
    git -c maintenance.auto=false -c gc.auto=0 fetch -q origin
  fi
}

# One publish per clone at a time (worktree mode). Creating a folder either succeeds or fails,
# at once, so two runs can never both take it. Any lock that exists stops the run, and a run
# never removes a lock it did not take: whether an old lock is safe to remove is the person's
# call, because a hard-killed run's push and gate can outlive it.
take_lock() {
  lock="$common/ship.lock"
  if mkdir "$lock" 2>/dev/null; then
    lock_taken=1
    if printf '%s\n' "$$" > "$lock/pid" 2>/dev/null && printf '%s\n' "$my_start" > "$lock/start" 2>/dev/null \
       && printf '%s\n' "$my_host" > "$lock/host" 2>/dev/null; then
      return 0
    fi
    rm -rf "$lock"; lock_taken=0
    echo "✗ Publish stopped — couldn't write this clone's publish lock ($lock)."
    echo "  Nothing was published and $here."
    exit 1
  fi
  if [ ! -d "$lock" ]; then
    echo "✗ Publish stopped — couldn't create this clone's publish lock ($lock): is the git folder"
    echo "  read-only, or the disk full? Nothing was published and $here."
    exit 1
  fi
  local pid start host state
  pid="$(cat "$lock/pid" 2>/dev/null)" || pid=""
  start="$(cat "$lock/start" 2>/dev/null)" || start=""
  host="$(cat "$lock/host" 2>/dev/null)" || host=""
  # Running means: that id exists with that same start time, so a reused id does not count. A
  # lock written on another computer (a shared disk) cannot be read as gone from here, nor can
  # one where ps cannot say; a computer's own name can change (on a Mac with no host name set,
  # `uname -n` gives a local network name, which macOS renames on a clash), so the name never
  # overrules a running match.
  if [ -z "$pid" ] || [ -z "$start" ] || [ -z "$my_start" ]; then state=unknown
  elif [ "$(proc_start "$pid")" = "$start" ]; then state=running
  elif [ "$host" != "$my_host" ]; then state=unknown
  else state=gone
  fi
  stop_point "Nothing was published and $here."   # a Ctrl-C may have ended the ps call above
  echo "✗ Publish stopped — another publish holds this clone's lock:"
  echo "    $lock"
  if [ -z "$pid" ]; then
    echo "  It names no process yet (a publish writes its own a moment after it takes the lock)."
  elif [ -z "$start" ]; then
    echo "  It names process $pid, with no start time."
  else
    echo "  It names process $pid${host:+ on $host}, started $start (UTC)."
  fi
  if [ "$state" = running ]; then
    echo "  That process is still running, so a publish is under way. Let it finish, and run"
    echo "  npm run ship again afterwards if you still need to."
  else
    if [ "$state" = gone ]; then
      echo "  That process is not running: the publish that took the lock was stopped hard"
      echo "  (killed, or the computer lost power) and never got to remove it."
    else
      echo "  This script cannot tell whether that publish is still running."
    fi
    echo "  A publish stopped hard can leave its push and its tests running on their own, in its"
    echo "  temporary copy. Check that no 'git push' from it is still running, then remove the"
    echo "  lock with:"
    echo "    rm -r '$lock'"
    echo "  and run npm run ship again."
  fi
  echo "  Nothing was published and $here."
  exit 1
}

# Leftovers. A run stopped hard (killed, a power cut) never gets to remove its worktree. Every
# run notes its worktree in ship's own list beside the lock before making it, and takes the line
# off once it has removed it, so a line left by an earlier run names a leftover. Read holding the
# lock and before this run adds its own line. A leftover never blocks a publish (every run makes
# a new folder) and ship never removes one, because a hard-killed run's push and gate can
# outlive it, still working in that folder: it says what it found and how to remove it. A line
# whose worktree is gone from disk and from git's records was removed by hand since, and goes.
# A worktree that is not on the list is never touched or reported, whatever its name or lock.
report_leftovers() {
  [ -s "$list" ] || return 0
  local wl line path rest pid start how whole kept="" seen=0 tab=$'\t'
  wl="$(git worktree list --porcelain)"
  while IFS= read -r line || [ -n "$line" ]; do
    [ -n "$line" ] || continue
    # Path, process id, start time: tab-separated, as this script writes them. A line cut short
    # (a full disk) lacks the later fields, and its path may name another folder: only a whole
    # line (all three fields, a numeric process id) naming a folder this script names gets a
    # command that removes it.
    path="${line%%"$tab"*}" pid="" start="" whole=0
    case "$line" in
      *"$tab"*"$tab"*)
        rest="${line#*"$tab"}"; pid="${rest%%"$tab"*}"; start="${rest#*"$tab"}"
        case "$pid" in ''|*[!0-9]*) ;; *) whole=1 ;; esac ;;
    esac
    case "${path##*/}" in ship-worktree.?*) ;; *) whole=0 ;; esac
    if grep -qxF "worktree $path" <<<"$wl"; then
      how="git worktree remove --force --force '$path'"
    elif [ -e "$path" ]; then
      how="rm -rf '$path'"   # made by mktemp, never a worktree
    else
      continue
    fi
    if [ "$whole" = 0 ]; then
      how="(check it by hand: not a whole line this script wrote; then delete the line from $list)"
    fi
    kept="$kept$line
"
    if [ "$seen" = 0 ]; then
      echo ""
      echo "⚠ Left over from an earlier publish that was stopped hard; this run leaves it alone:"
      seen=1
    fi
    if [ "$whole" = 1 ]; then echo "    $path  (made by process $pid${start:+, started $start UTC})"; else echo "    $path"; fi
    echo "      remove with:  $how"
  done < "$list"
  if [ "$seen" = 1 ]; then
    echo "  Remove one only once nothing is working in it any more: a publish stopped hard can"
    echo "  leave its push and its tests running there."
  fi
  if [ -z "$kept" ]; then rm -f "$list"; else printf '%s' "$kept" > "$list.new" && mv -f "$list.new" "$list"; fi
}

drop_list_line() { # <line>: takes it off ship's own list; leaves the list as it is if it can't
  [ -f "$list" ] || return 0
  local r=0
  grep -vxF -- "$1" "$list" > "$list.new" 2>/dev/null || r=$?
  case "$r" in
    0) mv -f "$list.new" "$list" ;;
    1) rm -f "$list.new" "$list" ;;
    *) rm -f "$list.new" ;;
  esac
}

# The script that publishes must be the one being published (worktree mode). The folder may be on
# any branch, with edits, so a half-edited or outdated copy of this file could otherwise publish.
# Compared by content (git's hash of each file), not by version line; this file's hash was the
# first thing this run took.
check_script() {
  local want mine theirs
  want="$(git rev-parse --verify -q "$id:scripts/ship.sh")" || want=""
  if [ -n "$self_blob" ] && [ "$self_blob" = "$want" ]; then return 0; fi
  mine="$(sed -n 's/^# template-version: *\([^ ]*\).*/\1/p' "${BASH_SOURCE[0]}" 2>/dev/null)" || mine=""
  theirs="$(git cat-file -p "$id:scripts/ship.sh" 2>/dev/null | sed -n 's/^# template-version: *\([^ ]*\).*/\1/p')" || theirs=""
  stop_point "Nothing was published and $here."   # a Ctrl-C may have ended a git call above
  echo ""
  echo "✗ Publish stopped — this folder's scripts/ship.sh is not the one on GitHub's main."
  if [ -z "$want" ]; then
    echo "  GitHub's main as of the fetch ($short) has no scripts/ship.sh."
  elif [ "$mine" != "$theirs" ]; then
    echo "  This folder's copy says template-version ${mine:-(none)}; GitHub's main as of the"
    echo "  fetch ($short) has ${theirs:-(none)}."
  else
    echo "  Both say template-version ${mine:-(none)}, but the two files differ anyway (an edit,"
    echo "  or a change that is not on GitHub's main yet)."
  fi
  echo "  The copy that publishes has to be the one being published, so nothing was"
  echo "  published, and this folder was not touched. Run it from a checkout that is up to"
  echo "  date with GitHub's main."
  exit 1
}

push_once() {
  if [ "$from_github" = 1 ]; then
    # The hooks folder is pinned for this one command, so the worktree's own committed pre-push
    # gate runs whatever the clone's shared core.hooksPath says: another session may have set it
    # its own way, or change it while this runs. SHIP_KEEP_HOOKS_PATH reaches the gate's own
    # install too, whose scripts/wire-hooks.mjs then leaves that shared setting alone.
    SHIP_KEEP_HOOKS_PATH=1 git -C "$wt" -c core.hooksPath=scripts/hooks push origin "$id:refs/heads/production"
  else
    git push origin "$id:refs/heads/production"
  fi
}

finish() { # <the last line of a run that went well>: the EXIT trap prints it, after its cleanup
  final_line="$1"
  if [ "$not_published" -gt 0 ]; then
    final_line="$final_line $not_published not published: in this folder, not on GitHub's main (listed above)."
  fi
}

# One trap for every way out. It saves the exit status first (a `set +e` would reset it to 0),
# then turns off stop-on-error and ignores the stop signals while it cleans up, so neither a
# failing step nor a second Ctrl-C skips the rest or turns a success into a failure. It removes
# only what this run made; a run in the folder's own mode makes neither a worktree nor a lock.
on_exit() {
  local status=$?
  set +e
  trap '' INT TERM HUP QUIT
  # A Ctrl-C that ended a git call before the push can stop the run through set -e, without a
  # word: say what is true.
  if [ "$status" != 0 ] && [ "$stop_asked" = 1 ] && [ "$stop_said" = 0 ] && [ "$push_started" = 0 ]; then
    echo ""
    echo "✗ Publish stopped — a stop was asked for (Ctrl-C, or a terminate signal)."
    echo "  Nothing was published and $here."
  fi
  if [ -n "$wt" ]; then
    if [ "$wt_added" = 1 ] && ! git worktree remove --force --force "$wt" >/dev/null 2>&1; then
      # git could not remove it. The folder is this run's own: its path came from this run's
      # mktemp call, never from a list or a name. So delete it, then the record, by path.
      rm -rf "$wt"
      git worktree remove --force --force "$wt" >/dev/null 2>&1
      if registered "$wt"; then
        echo "⚠ git kept its record of this run's temporary copy ($wt). Remove it with:"
        echo "    git worktree remove --force --force '$wt'"
      else
        echo "⚠ git could not remove this run's temporary copy, so this run deleted it ($wt) and git's record of it."
      fi
    elif [ -d "$wt" ]; then
      rm -rf "$wt"   # made by mktemp, never (fully) a worktree
    fi
    if [ -n "$my_line" ] && ! registered "$wt"; then drop_list_line "$my_line"; fi
  fi
  # Removed only if it still names this run: someone may have removed it by hand meanwhile, and
  # another run taken it.
  if [ "$lock_taken" = 1 ] && [ "$(cat "$lock/pid" 2>/dev/null)" = "$$" ] \
     && [ "$(cat "$lock/start" 2>/dev/null)" = "$my_start" ]; then
    rm -rf "$lock"
  fi
  [ -z "$push_status" ] || rm -f "$push_status" 2>/dev/null
  # Kept on a failure once the push has started: it is the evidence for "may or may not have
  # landed", and the screen may be gone.
  if [ -n "$git_log" ]; then
    if [ "$status" != 0 ] && [ "$push_started" = 1 ] && [ -s "$git_log" ]; then
      echo "  git's output from this run is kept in $git_log"
    else
      rm -f "$git_log"
    fi
  fi
  # The last line: a run that went well says it in full; in worktree mode any other run that got
  # as far as reading GitHub's main names that commit, and how many files stayed behind.
  if [ -n "$final_line" ]; then
    echo "$final_line"
  elif [ "$from_github" = 1 ] && [ -n "$id" ]; then
    if [ "$not_published" -gt 0 ]; then
      echo "  (GitHub's main as of the fetch: ${id:0:12}. $not_published not published from this folder, listed above.)"
    else
      echo "  (GitHub's main as of the fetch: ${id:0:12}.)"
    fi
  fi
  exit "$status"
}

ship() {
set -euo pipefail

# First of all, git's hash of this very file, the one bash has just read: worktree mode compares
# it with GitHub's copy (check_script). Taken any later, a file another session swapped in
# meanwhile could pass for the one running.
self_blob="$(git hash-object -- "${BASH_SOURCE[0]}" 2>/dev/null)" || self_blob=""

# Read from this clone's own config only (--local): a value in someone's global config must not
# switch a fresh clone (a beginner's, a new owner's) out of the folder checks below.
from_github=0
if raw="$(git config --local --get ship.fromGitHub 2>/dev/null)"; then
  bool="$(git config --local --bool --get ship.fromGitHub 2>/dev/null)" || bool=""
  case "$bool" in
    true) from_github=1 ;;
    false) ;;
    *)
      echo "✗ Publish stopped — this clone's ship.fromGitHub setting is '$raw', which git reads as"
      echo "  neither true nor false. Nothing was published. Set it with  git config ship.fromGitHub true"
      echo "  (or false), or remove it with  git config --unset ship.fromGitHub"
      exit 1 ;;
  esac
fi
# What every "nothing was published" message adds about the state you are in now.
if [ "$from_github" = 1 ]; then here="this folder was not touched"; else here="you're still safely on 'main'"; fi

# All the EXIT trap may clean up, empty until this run makes it.
git_log="" push_status="" wt="" wt_added=0 lock="" lock_taken=0 list="" my_line="" my_start=""
my_host="" push_started=0 stop_asked=0 stop_said=0 final_line="" id="" short="" not_published=0
# A stop (Ctrl-C, or a terminate signal) is only NOTED, and bash runs the note once the step in
# the foreground ends. The script kills nothing itself: a Ctrl-C still reaches git and the gate
# exactly as it always did, and a terminate sent to the script alone lets the current step
# finish, so the worktree is never removed under a running gate. After each step the script
# looks at the note and stops there, saying what is true at that point.
trap 'stop_asked=1' INT TERM HUP QUIT
trap on_exit EXIT

if [ "$from_github" = 0 ]; then
  branch="$(git rev-parse --abbrev-ref HEAD)"
  if [ "$branch" != "main" ]; then
    echo "✗ Run this from 'main' (you're on '$branch'). Try: git checkout main"; exit 1
  fi
  if [ -n "$(git status --porcelain)" ]; then
    echo "✗ You have unsaved changes. Save + upload them first:"
    echo "    git add -A && git commit -m \"...\" && git push"; exit 1
  fi
else
  # The clone's shared git folder as a full path: git prints a relative one in a primary
  # checkout. The lock and the list of this script's worktrees live there.
  common="$(git rev-parse --git-common-dir)"
  common="$(CDPATH= cd -- "$common" && pwd -P)"
  list="$common/ship-worktrees"
  my_start="$(proc_start "$$")"
  my_host="$(uname -n 2>/dev/null)" || my_host=""
  take_lock
fi
# Everything below needs an up-to-date view of the remote: the origin/production
# existence check, the local-vs-GitHub comparison, and the divergence check further
# down, which answers a question about the REMOTE from a local ref. A stale ref would
# let those answer confidently and wrongly. `set -e` would abort here on its own, but
# with a raw git error and no guidance — the wrong ending for the most likely way a
# publish fails before it even starts.
#
# So capture git's stderr and read it: a network failure is retried once and, if it
# fails again, reported as a blip; anything else is printed in full and stops the
# publish immediately, because retrying a missing remote or a dead credential just
# adds five seconds to the same answer.
#
# One scratch file, reused by the push below, so there is a single EXIT trap rather
# than two that would silently replace each other. Each mktemp call is checked, and named
# so tests/check_ship_push.sh can fail each in turn.
tmp_base="${TMPDIR:-/tmp}"; tmp_base="${tmp_base%/}"
git_log="$(mktemp "$tmp_base/ship-log.XXXXXX")" || no_temp
push_status="$(mktemp "$tmp_base/ship-status.XXXXXX")" || no_temp
if [ "$from_github" = 1 ]; then
  # The folder the worktree goes into, further down; made here with the other scratch files, so
  # a failing mktemp stops the run before anything else happens.
  wt="$(mktemp -d "$tmp_base/ship-worktree.XXXXXX")" || no_temp
  if wt_real="$(real_dir "$wt")" && [ -n "$wt_real" ]; then wt="$wt_real"; fi
fi
if fetch_origin 2>"$git_log"; then fetch_ok=1; else fetch_ok=0; fi
stop_point "Nothing was published and $here."
if [ "$fetch_ok" = 0 ]; then
  # Only a NETWORK failure is worth a silent retry. A missing remote or expired
  # credentials would fail again five seconds later, and calling that "a network blip"
  # is the same misdiagnosis this script exists to stop making — so say it at once,
  # with git's own error, instead of hiding it behind a wait.
  #
  # Order matters, exactly as it does in the push classifier below. A misconfigured
  # remote ALSO ends in "fatal: Could not read from remote repository" — `git fetch`
  # with a bad origin prints "does not appear to be a git repository" and then that
  # line — so the not-a-network cases have to be taken out first, or the transport
  # pattern claims them. (Caught by tests/check_ship_push.sh, not by inspection.)
  view="$(log_view "$git_log")"
  if looks_like_local_or_auth_failure "$view"; then
    fetch_is_network=0
  elif looks_like_network_failure "$view"; then
    fetch_is_network=1
  else
    # Unrecognised: don't retry. Same call the push classifier makes — an unknown
    # failure is not evidence of a blip, and a wrong retry costs a wait and a lie.
    fetch_is_network=0
  fi
  if [ "$fetch_is_network" = 1 ]; then
    echo "⚠ Couldn't reach GitHub — retrying once."
    # A Ctrl-C ends the wait, not the script, so the note is read.
    sleep 5 || true
    stop_point "Nothing was published and $here."
    if fetch_origin; then refetch_ok=1; else refetch_ok=0; fi
    stop_point "Nothing was published and $here."
    if [ "$refetch_ok" = 0 ]; then
      echo ""
      echo "✗ Publish stopped — couldn't fetch from GitHub, so nothing was checked."
      echo "  Every check below this point needs a current view of what's on GitHub, so"
      echo "  continuing could publish against stale information."
      echo "  Nothing was published and $here."
      echo "  This is almost always a network blip. Try again:  npm run ship"
      exit 1
    fi
  else
    # Same stream as the explanation below it: an owner capturing `npm run ship > log`
    # to send to whoever is helping must not get "the error is printed just above"
    # with nothing above it.
    cat "$git_log"
    echo ""
    echo "✗ Publish stopped — 'git fetch' failed, and not for a network reason."
    echo "  git's own error is printed just above — that's the one to read. A missing"
    echo "  'origin' remote and expired credentials both land here, and neither is"
    echo "  fixed by trying again."
    echo "  Nothing was published and $here."
    exit 1
  fi
fi
# From here to the push, a Ctrl-C can end one of the git calls below, and its failure would read
# as a verdict about the branches. So each verdict looks at the note first.
if ! git rev-parse --verify -q origin/production >/dev/null; then
  stop_point "Nothing was published and $here."
  echo "✗ No 'production' branch on GitHub yet — this site isn't set up two-stage."; exit 1
fi
if [ "$from_github" = 0 ]; then
  # Your copy and GitHub's must match before publishing — but WHICH WAY they differ
  # decides what to do about it, and a plain `!=` can't tell. Telling someone whose copy
  # is BEHIND to "run git push" sends them to the one command that cannot help (and that
  # git will then reject), so ask which side moved and say the matching thing.
  upstream="$(git rev-parse '@{u}' 2>/dev/null || true)"
  stop_point "Nothing was published and $here."
  if [ -z "$upstream" ]; then
    echo "✗ This branch isn't connected to GitHub yet. Run: git push -u origin main"; exit 1
  fi
  if [ "$(git rev-parse @)" != "$upstream" ]; then
    if git merge-base --is-ancestor @ "$upstream"; then moved=behind
    elif git merge-base --is-ancestor "$upstream" @; then moved=ahead
    else moved=both
    fi
    stop_point "Nothing was published and $here."
    if [ "$moved" = behind ]; then
      echo "✗ GitHub has changes that aren't on your computer yet — publishing now would"
      echo "  put an OLDER version of the site live. Get them first:  git pull"
    elif [ "$moved" = ahead ]; then
      echo "✗ Your latest changes aren't uploaded yet. Run: git push"
    else
      echo "✗ Your copy and GitHub's have BOTH changed since they last matched."
      echo "  Sort that out before publishing:  git pull --no-rebase"
      echo "  (--no-rebase because plain 'git pull' refuses to guess when both sides have"
      echo "  moved.) If it then mentions a 'conflict', ask for help rather than guessing."
      echo "  Once it's clean:  git push"
    fi
    exit 1
  fi
  # The commit this run publishes, read once: the push and the live check use this id, so a
  # commit landing on `main` mid-publish cannot change what is pushed or verified. (The gate
  # still builds this folder, so a change made here mid-publish can still change what is
  # tested; only the worktree mode closes that.) Not origin/main's id: `main`'s upstream need
  # not be origin/main, and the checks above are about that upstream.
  id="$(git rev-parse @)"
  echo "→ Publishing main → production. This goes LIVE."
else
  # GitHub's main as of the fetch, read once; `main` may move on during the run, so the first
  # and the last line name the commit. "Main is pushed" holds by construction: the commit came
  # from GitHub. So the branch and upstream checks above are skipped, and this folder's unsaved
  # files and unpushed commits are listed below instead.
  id="$(git rev-parse --verify 'refs/remotes/origin/main^{commit}')"
  short="${id:0:12}"
  echo "→ Publishing GitHub's main as of the fetch ($short) → production, from a temporary copy; this folder is ignored. This goes LIVE."
  check_script
  report_leftovers
fi
# Push the commit straight to the remote production branch — no local checkout, so a failure
# (rejected push, red pre-push gate, network) never strands the owner on production.
#
# Whether the branches diverged is a question that can be answered LOCALLY, from the
# fetch above — so answer it before touching the network, instead of inferring it from
# a failed push. That order is the whole point: a push fails for plenty of reasons that
# have nothing to do with the branches, and reporting those as "production has commits
# main doesn't" sends the owner hunting a conflict that isn't there, while warning them
# off the one thing that actually works — running it again. Seen in production: an SSH
# timeout to github.com printed the divergence message while production was simply two
# commits behind main and cleanly fast-forwardable.
if ! git merge-base --is-ancestor origin/production "$id"; then
  stop_point "Nothing was published and $here."
  echo ""
  if [ "$from_github" = 1 ]; then
    echo "✗ Publish blocked — 'production' has commits that GitHub's 'main' doesn't have."
  else
    echo "✗ Publish blocked — 'production' has commits that 'main' doesn't have."
  fi
  echo "  (e.g. it was published from elsewhere, or kept history from an older ship flow.)"
  echo "  Nothing was published and $here. Do NOT force-push —"
  echo "  ask for help to reconcile the two branches."
  exit 1
fi

if [ "$from_github" = 1 ]; then
  # The worktree: detached at the commit, so it can exist while another worktree has `main`
  # checked out. Its line goes on ship's list before git makes the worktree in its folder, so a
  # hard kill at any point after leaves a line the next run reports. (A kill before leaves at
  # most the empty folder from mktemp, in the temp folder.)
  my_line="$(printf '%s\t%s\t%s' "$wt" "$$" "$my_start")"
  printf '%s\n' "$my_line" >> "$list"
  # The hooks folder is pinned, for this one command, to a path that cannot exist (one below a
  # file, outside the checkout, so no commit can put hooks there), so making the worktree runs
  # no hook (git would run post-checkout, post-index-change and reference-transaction): the
  # clone's shared setting may name another session's folder, and a hook there could install
  # packages and so rewrite that very setting.
  if git -c core.hooksPath="$push_status/no-hooks" worktree add -q --detach "$wt" "$id"; then wt_added=1; else wt_added=0; fi
  stop_point "Nothing was published and $here."
  if [ "$wt_added" = 0 ]; then
    echo ""
    echo "✗ Publish stopped — couldn't make the temporary copy (git worktree add; git's error is above)."
    echo "  Nothing was published and $here."
    exit 1
  fi
  # What stays behind: read with git's optional locks off, because plain `git status` rewrites
  # the index, taking its lock for a moment, and another session's `git add` may need it then.
  st="$(git --no-optional-locks status --porcelain)"
  if [ -n "$st" ]; then
    not_published="$(grep -c '' <<<"$st")"
    echo ""
    echo "Not published: in this folder, not on GitHub's main"
    awk 'NR <= 20 { print "    " $0 }' <<<"$st"
    if [ "$not_published" -gt 20 ]; then echo "    … and $((not_published - 20)) more"; fi
  fi
  if git show-ref --verify -q refs/heads/main; then
    ahead="$(git rev-list --count refs/remotes/origin/main..refs/heads/main)"
    if [ "$ahead" -gt 0 ]; then
      if [ "$ahead" = 1 ]; then word=commit; else word=commits; fi
      echo ""
      echo "Not published: this computer's 'main' has $ahead $word that GitHub's main doesn't."
      echo "  If they should go live, get them onto GitHub's main first (a pull request, or a"
      echo "  push where direct pushes to 'main' are allowed), then run npm run ship again."
    fi
  fi
  # Nothing goes live in this mode without the commit's own pre-push hook having run (what the
  # hook checks is the site's own choice).
  if [ ! -x "$wt/scripts/hooks/pre-push" ]; then
    echo ""
    echo "✗ Publish stopped — GitHub's main as of the fetch ($short) has no runnable"
    echo "  scripts/hooks/pre-push. This mode publishes only once the commit's own pre-push"
    echo "  check has run, and without the hook nothing would run."
    echo "  Nothing was published and $here."
    exit 1
  fi
  # The exact packages of the commit, so the gate tests what goes live (npm ci never rewrites
  # the lockfile). Its prepare step, scripts/wire-hooks.mjs, would write core.hooksPath, which
  # every worktree of this clone shares and another session may rely on; SHIP_KEEP_HOOKS_PATH
  # makes it leave that setting alone.
  stop_point "Nothing was published and $here."
  echo ""
  echo "→ Installing the site's packages in the temporary copy (npm ci)…"
  if ( CDPATH= cd -- "$wt" && SHIP_KEEP_HOOKS_PATH=1 npm ci --no-audit --no-fund ); then install_ok=1; else install_ok=0; fi
  stop_point "Nothing was published and $here."
  if [ "$install_ok" = 0 ]; then
    echo ""
    echo "✗ Publish stopped — installing the site's packages in the temporary copy failed"
    echo "  (npm ci; npm's error is above). This mode installs them fresh for every publish,"
    echo "  so it needs the npm registry, or packages npm has cached before."
    echo "  Nothing was published and $here."
    exit 1
  fi
fi

# Divergence is settled above, so what remains is either a transport failure or a red
# pre-push gate — and those don't want the same response. A dead network wants "run it
# again"; a red gate wants "read the test output"; a connection that dies mid-upload
# can't honestly be called either way. So read git's own words and say which it was.
# `tee` keeps every line — including the pre-push build and test output — on screen
# while capturing it; nothing git says is swallowed either way.
#
# git's own exit status is written down by the push step itself, into a scratch file inside
# the same pipeline, and never read back from the pipeline afterwards: on bash 3.2 (the Mac's
# own) a stop noted the moment a pipeline ends resets its per-command status, and a failed push
# then read as a success. Reading the pipeline's status would also let a failed `tee` (a full
# temp filesystem) turn a push that went out into "nothing was published". An empty or missing
# status (an interrupt ended the step before it wrote one, or the disk is full) is never read as
# a success, nor as "nothing was published".
stop_point "Nothing was published and $here."   # the last look before anything leaves this computer
push_tries=2
kind=""
for attempt in $(seq 1 "$push_tries"); do
  : > "$push_status" 2>/dev/null || true
  push_started=1
  { push_once 2>&1 && rc=0 || rc=$?; echo "$rc" > "$push_status"; } | tee "$git_log" || true
  push_rc="$(cat "$push_status" 2>/dev/null)" || push_rc=""
  case "$push_rc" in ''|*[!0-9]*) push_rc="" ;; esac
  view="$(log_view "$git_log")"
  # Classify from git's own words, anchored on the LINES git actually emits rather than
  # on bare phrases: the pre-push gate (a full build plus the test suite) writes into
  # this same log, so a failing test that quotes "rejected"/"fetch first" — or one that
  # reports "timed out" — must not be read as a divergence or as a dead network.
  if [ -z "$push_rc" ]; then
    kind=unknown
  elif [ "$push_rc" = 0 ]; then
    kind=ok
  elif grep -q '^▶ pre-push gate' <<<"$view" && ! grep -q '^✓ pre-push gate passed' <<<"$view"; then
    # FIRST, because it decides whether anything else in this log came from git at all.
    # The gate ran and did not pass, so the push never reached the network: every other
    # arm below is about what the REMOTE said, and the remote never got a word in.
    # Anchoring a pattern to the start of a line proves its shape, never its author —
    # this is the only check here that establishes provenance.
    kind=gate
  elif grep -qE '^ *! \[rejected\].*\((non-fast-forward|fetch first|stale info)\)|^hint: Updates were rejected' <<<"$view" \
       || { grep -qE '^ *! \[remote rejected\].*\((failed to update ref|incorrect old value provided)\)' <<<"$view" \
            && grep -qE "^remote: error: cannot lock ref 'refs/heads/production': is at [0-9a-f]+ but expected [0-9a-f]+" <<<"$view"; }; then
    # The check above ruled out a pre-existing divergence seconds ago, so this is the
    # narrow race it cannot cover: production moved WHILE this was publishing. Moved before
    # the push started, git refuses it itself ("fetch first"); moved while the pre-push gate
    # ran, the remote refuses the update it was sent, with "failed to update ref" (git 2.33)
    # or "incorrect old value provided" (the newer git on GitHub's runners). git 2.33 uses
    # its words for any ref it could not write, so either counts only beside the remote's own
    # line that production is at one commit where another was expected, which both print in
    # a race. GitHub's wording is not checked, and would land in "can't name".
    kind=raced
  elif looks_like_local_or_auth_failure "$view"; then
    # An SSH key, host-key or access problem also ends in "Could not read from remote
    # repository", so take it out of the connectivity arms below: re-running changes
    # nothing, and "your network blipped" would be its own misdiagnosis.
    kind=auth
  elif grep -qE '^(fatal: ([Tt]he remote end hung up|early EOF)|error: RPC failed; curl [0-9]+|send-pack: unexpected disconnect)' <<<"$view"; then
    # Dropped MID-TRANSFER: the connection was alive, so GitHub may already have taken
    # the update. Note WHY this doesn't retry, because the obvious reason is wrong — a
    # repeated non-force push of the same ref IS idempotent (it lands, or says
    # "Everything up-to-date", or is rejected if someone else moved the branch), so a
    # retry would be safe. It is not free: the pre-push gate has already run by this
    # point, so retrying spends another full build and test run on a state nobody can
    # describe yet. Handing that call to the owner, with a re-run that self-diagnoses in
    # one line, costs less than guessing on their behalf.
    kind=dropped
  elif looks_like_network_failure "$view"; then
    kind=unreachable
  else
    kind=other
  fi
  # Only a failure at CONNECT time is worth retrying, and only that one is cheap: git
  # connects to the remote before it runs the pre-push hook, so the build and the tests
  # never ran. Every other case would fail the same way two minutes later. Nor after a stop.
  if [ "$kind" != unreachable ] || [ "$stop_asked" = 1 ] || [ "$attempt" -ge "$push_tries" ]; then break; fi
  echo ""
  echo "⚠ Couldn't reach GitHub. Nothing was published — retrying in 5s ($((attempt+1))/$push_tries)…"
  sleep 5 || true
  if [ "$stop_asked" = 1 ]; then break; fi
done

site="$(grep -oE "site:[[:space:]]*['\"]https?://[^'\"]+" "${wt:-.}/astro.config.mjs" 2>/dev/null | sed -E "s/site:[[:space:]]*['\"]//" | head -1 || true)"
# Strip a trailing slash: a misconfigured SITE.url ('https://x.com/') would build
# 'https://x.com//build.txt' — NOT reliably safe (varies by host; some hosts
# 307-redirect a double slash). curl -L below now follows such redirects, but keep
# the normalization: same as the llms-coverage guard applies to SITE.url.
site="${site%/}"
build_txt="${site:-your live site}/build.txt"
# A *.pages.dev address is Cloudflare's own address for the project: serving the build there
# does not show the site is live on its own domain, so the success line must not say LIVE.
site_host="${site#*://}"; site_host="${site_host%%/*}"; site_host="${site_host%%:*}"
site_host="$(tr '[:upper:]' '[:lower:]' <<<"${site_host%.}")"
case "$site_host" in
  *.pages.dev)
    ok_line="✓ Published — verified on the pages.dev address:"
    ok_note=" That's Cloudflare's address for the site, not your own domain: the site is live on your domain only once that's connected." ;;
  *) ok_line="✓ LIVE — verified:"; ok_note="" ;;
esac

# After a stop, the log may be cut short (its writer stops too), so a line found in it counts
# and a line missing from it proves nothing. Only the arms that rest on git's own words stand:
# production moved, GitHub unreachable at connect time, a login or host-key failure. A gate
# that started without its pass line proves nothing either: it may have failed, or the line was
# never written.
if [ "$stop_asked" = 1 ]; then
  case "$kind" in
    ok|raced|unreachable|auth) ;;
    *) kind=maybe ;;
  esac
  echo ""
  echo "✗ Publish stopped — a stop was asked for (Ctrl-C, or a terminate signal) during the push."
fi
if [ "$kind" = unknown ]; then kind=maybe; fi

if [ "$kind" != ok ]; then
  # EVERY message below says two things, and a new arm must say both: what went wrong,
  # and WHAT STATE YOU ARE IN NOW. The cause alone is only half an answer — someone who
  # has just been told "the connection dropped" still doesn't know whether their site
  # changed, whether anything needs undoing, or what is safe to run next.
  #
  # Better still, where it is possible: LEAVE NO STATE TO DESCRIBE. This script gets
  # that for free — it pushes a commit to production without checking anything out, so a
  # failure cannot leave a half-finished local merge behind. A deploy script that DOES
  # need a local merge should restore the branch to its pre-merge tip after a failed
  # push rather than explain the drift: a state that no longer exists needs no
  # explanation and cannot trip the next run. Prefer undoing to documenting; document
  # only what you cannot undo — which is why `dropped` below refuses to guess.
  echo ""
  case "$kind" in
    raced)
      echo "✗ 'production' moved while this was publishing, so GitHub refused the push."
      echo "  Nothing was published and $here. Do NOT force-push —"
      echo "  run it again, and the check at the start will look at the new state and tell"
      echo "  you where things stand:"
      echo "    npm run ship"
      ;;
    unreachable)
      if [ "$attempt" = 1 ]; then tries="1 try"; else tries="$attempt tries"; fi
      echo "✗ Couldn't reach GitHub — a network or SSH problem, not a branch problem."
      echo "  Nothing was published and $here ($tries;"
      echo "  git's own error is printed above). Nothing to reconcile, nothing to fix —"
      echo "  wait a moment, then run it again:"
      echo "    npm run ship"
      ;;
    dropped)
      echo "✗ The connection to GitHub dropped part-way through the upload."
      echo "  git's own error is printed above. This one is genuinely unclear — the"
      echo "  upload may or may not have completed — so this script won't guess."
      echo "  Run it again:"
      echo "    npm run ship"
      echo "  If it already landed, git says 'Everything up-to-date' and the live-site"
      echo "  checks run as normal."
      ;;
    maybe)
      if [ "$stop_asked" = 1 ]; then
        echo "  The push was cut short, so the publish may or may not have landed."
      else
        echo "✗ This script could not read git's result for the push (the file it writes it"
        echo "  to is empty or missing: a full disk?), so the publish may or may not have landed."
      fi
      echo "  git's own output is above, and may be cut short. Run it again:"
      echo "    npm run ship"
      echo "  If it already landed, git says 'Everything up-to-date' and the live-site"
      echo "  checks run as normal."
      ;;
    auth)
      if [ "$stop_asked" = 1 ]; then
        echo "✗ The push failed: GitHub did not accept the login (an SSH key, a host key or a"
        echo "  password). git's own error is printed above — that's the one to read; trying"
        echo "  again will not fix it."
        echo "  Nothing was published and $here."
      else
        echo "✗ The push failed, for a reason this script can't name."
        echo "  git's own error is printed above — that's the one to read. A red pre-push"
        echo "  gate (the build or the tests) lands here too and prints its failure above."
        echo "  Nothing was published and $here."
      fi
      ;;
    *)
      echo "✗ The push failed, for a reason this script can't name."
      echo "  git's own error is printed above — that's the one to read. A red pre-push"
      echo "  gate (the build or the tests) lands here too and prints its failure above."
      echo "  Nothing was published and $here."
      # Playwright's own words when the test server's port is taken. The port comes from the
      # site's folder (playwright.config.ts), so another run in this same folder can hold it.
      if grep -q 'is already used' <<<"$view"; then
        echo "  The site's test port was taken (\"is already used\" above): another test run, a"
        echo "  preview of the site (npm run dev or npm run preview), or a test server left"
        echo "  behind by a stopped run holds it. Close that, then run npm run ship again."
      fi
      ;;
  esac
  exit 1
fi
if [ "$stop_asked" = 1 ]; then
  echo "  The publish went out: GitHub's production is now ${id:0:12}."
  echo "  The live-site check was skipped, so nothing has confirmed the live site serves"
  echo "  it yet. In a few minutes, $build_txt should show $id."
  exit 1
fi
echo "✓ Pushed. Cloudflare is building the live site now."

# Push ≠ live: Cloudflare can silently stop building (webhook auth lapse — seen in
# production 2026-07-02: two green pushes, no deploy for 40+ min). So VERIFY: the
# build writes its commit SHA to /build.txt (scripts/build-marker.mjs); poll the
# live site until it serves the SHA we just pushed. Cache-busted query so the edge
# cache can't show us a stale answer. In worktree mode the site's address is read from
# the published copy.
if [ -z "$site" ]; then
  echo "⚠ Couldn't read the site URL from astro.config.mjs — can't verify the deploy."
  if [ "$from_github" = 1 ]; then
    finish "  Check it yourself in ~2 min: your live URL should show GitHub's main as of the fetch ($short)."
  else
    finish "  Check it yourself in ~2 min: your live URL should show the change."
  fi
  exit 0
fi
echo "→ Verifying the live site serves this exact build (up to 4 min)…"
for i in $(seq 1 24); do
  # A Ctrl-C ends the wait (or the request), not the script, so the note is read.
  sleep 10 || true
  stop_live=0; [ "$stop_asked" = 1 ] && stop_live=1
  if [ "$stop_live" = 0 ]; then
    # -L: follow 3xx so a domain-level redirect (naked → www) can't yield an empty
    # body and a false "old build" verdict; the exact-SHA match keeps the check honest.
    live="$(curl -sfL -m 8 "$site/build.txt?cb=$RANDOM$i" 2>/dev/null | tr -d '[:space:]')" || true
    [ "$stop_asked" = 1 ] && stop_live=1
  fi
  if [ "$stop_live" = 1 ]; then
    echo ""
    echo "✗ Stopped during the live-site check. The publish went out (GitHub's production is"
    echo "  now ${id:0:12}); only the check was stopped. In a few minutes, $build_txt"
    echo "  should show $id."
    exit 1
  fi
  if [ "$live" = "$id" ]; then
    if [ "$from_github" = 1 ]; then
      # Another clone may have published meanwhile, and Cloudflare then builds both. One more
      # look at GitHub's production; ls-remote starts no housekeeping, unlike a fetch.
      now="$(git ls-remote origin refs/heads/production 2>/dev/null)" || now=""
      now="${now%%[[:space:]]*}"
      if [ -n "$now" ] && [ "$now" != "$id" ]; then
        echo "⚠ A newer publish followed: GitHub's production is now ${now:0:12}. Which of the"
        echo "  two builds the live site ends on depends on Cloudflare, which this script does"
        echo "  not check: $build_txt shows the commit it serves."
      fi
      finish "$ok_line $site is serving GitHub's main as of the fetch ($short), after $((i*10))s.$ok_note"
    else
      finish "$ok_line $site is serving build ${id:0:12} (after $((i*10))s).$ok_note"
    fi
    exit 0
  fi
done
echo ""
echo "⚠ Pushed OK, but after 4 minutes the live site still serves an OLD build."
echo "  This usually means Cloudflare didn't build (it can stop silently). Check:"
echo "  Cloudflare dashboard → Workers & Pages → your project → Deployments."
echo "    • A failed deployment for ${id:0:12} → open its log, then 'Retry deployment'."
echo "    • NO deployment for it → Settings → Builds: unpause / re-connect the GitHub"
echo "      integration, then 'Create deployment' from 'production'."
echo "  (Brand-new site whose domain isn't connected yet? Then this is expected —"
echo "  verify via the project's *.pages.dev URL instead.)"
exit 1
}

ship "$@"; exit "$?"
