# Evidence for SKILL-PLAN-review-base-ancestor-guard.md

## READ E1: every --base use, run on a throwaway repository

The script that ran (verbatim):
```bash
#!/usr/bin/env bash
# Evidence for the plan: each legitimate --base use, run through the CURRENT independent_review.sh
# with a stub codex, in a throwaway repo whose origin is a bare repo beside it. For each: the exit
# code of the script and of `git merge-base --is-ancestor <base> HEAD` (0 = ancestor).
set -u
SKILL="$1"; SCRIPT="$SKILL/scripts/independent_review.sh"; ML="$SKILL/scripts/merge_link.sh"; SW="$SKILL/scripts/sweep_claims.sh"
T="$(mktemp -d "${TMPDIR:-/tmp}/base-uses.XXXXXX")"; T="$(cd "$T" && pwd -P)"
mkdir -p "$T/bin" "$T/u/.codex"; : >"$T/u/.codex/auth.json"; printf 'model = "stub-codex"\n' >"$T/u/.codex/config.toml"
printf '#!/bin/sh\nprintf "%%s\\n" "- NIT: stub"\n' >"$T/bin/codex"; chmod +x "$T/bin/codex"
printf '| id | Sev |\n|---|---|\n| R1 | NIT |\n' >"$T/prior.md"
export GIT_CONFIG_NOSYSTEM=1 HOME="$T/u" GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@example.invalid GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@example.invalid
g() { git -C "$W" "$@"; }; set1() { perl -pi -e "\$_=\"$1\\n\" if \$.==1" "$W/a.md"; }; c() { g add -A && g commit -q -m "$1"; }
run() {  # run <label> <diff file> <args...>
  local label="$1" f="$2"; shift 2
  ( cd "$W" && env -u CODEX_MODEL -u OLLAMA_MODEL -u MELIOUS_MODEL -u SECOND_SEAT PATH="$T/bin:$PATH" WITH_ANTIGRAVITY=0 REVIEW_LOG=off \
      REVIEW_RAW_DIR="$T/raw" bash "$SCRIPT" "$f" --seat codex --depth normal "$@" ) >"$T/out" 2>"$T/err"; rc=$?
  echo "== $label"; echo "   args: $*"; echo "   script exit: $rc"
  grep -h '^base:' "$T/out" | sed 's/^/   /'; grep -h '^Base check:' "$T/err" | sed 's/^/   /'
}
anc() { g merge-base --is-ancestor "$1" HEAD; echo "   is-ancestor $2 HEAD: exit $?"; }
onmain() { local r n; n="$(g symbolic-ref --short refs/remotes/origin/HEAD)"; g merge-base --is-ancestor "$1" refs/remotes/origin/HEAD; r=$?; echo "   is-ancestor $2 origin/HEAD ($n): exit $r"; }

git init -q --bare "$T/origin.git"; git -C "$T/origin.git" symbolic-ref HEAD refs/heads/main
W="$T/w"; git init -q "$W"; g symbolic-ref HEAD refs/heads/main
printf 'a one\nline 2\nline 3\nline 4\nline 5\n' >"$W/a.md"; printf 'b one: this always holds.\n' >"$W/b.md"; c A; A="$(g rev-parse HEAD)"
g remote add origin "$T/origin.git"; g push -q origin main; g remote set-head origin main
g checkout -q -b feat; set1 'a two'; c F1; F1="$(g rev-parse HEAD)"
git clone -q "$T/origin.git" "$T/o2"; printf 'b two\n' >"$T/o2/b.md"
git -C "$T/o2" commit -qam M1 && git -C "$T/o2" push -q origin main; g fetch -q origin; M1="$(g rev-parse origin/main)"
echo "A=$A F1=$F1 M1(origin/main)=$M1"

echo; echo "### 1. The misfire: main moved past the branch; two-dot diff, --base origin/main"
g diff origin/main HEAD >"$T/two.diff"; echo "   two-dot diff touches: $(grep '^diff --git' "$T/two.diff" | tr '\n' ' ')"
run "two-dot, --base origin/main" "$T/two.diff" --base origin/main; anc origin/main origin/main; onmain origin/main origin/main
echo; echo "### 1v. The incident's round 5: the same two-dot diff and --base origin/main, in a --verify round"
run "two-dot, --verify --base origin/main" "$T/two.diff" --verify "$T/prior.md" --base origin/main --round 2; anc origin/main origin/main; onmain origin/main origin/main

echo; echo "### 2. The whole change: three-dot diff, no --base (fetches the bare origin)"
g diff origin/main...HEAD >"$T/three.diff"; run "three-dot, no --base" "$T/three.diff"; anc "$A" "merge-base(=A)"

echo; echo "### 3. Delta since a reviewed head (F1): --verify --base F1"
set1 'a three'; c F2; F2="$(g rev-parse HEAD)"
g diff "$F1"..HEAD >"$T/delta.diff"; run "delta, --verify --base F1" "$T/delta.diff" --verify "$T/prior.md" --base "$F1" --round 2; anc "$F1" F1

echo; echo "### 4. Wording pass since the last reviewed head (F2): --wording-pass --base F2"
set1 'a four'; c F3; F3="$(g rev-parse HEAD)"
g diff "$F2"..HEAD >"$T/wp.diff"; run "wording pass, --base F2" "$T/wp.diff" --wording-pass --base "$F2"; anc "$F2" F2

echo; echo "### 5. Working-tree change on top of HEAD: --base HEAD"
set1 'a five (uncommitted)'; g diff HEAD >"$T/wt.diff"; run "working tree, --base HEAD" "$T/wt.diff" --base HEAD; anc HEAD HEAD
g checkout -q -- a.md

git -C "$T/o2" pull -q; perl -pi -e '$_="line 5 from main\n" if $.==5' "$T/o2/a.md"; git -C "$T/o2" commit -qam M2 && git -C "$T/o2" push -q origin main; g fetch -q origin; M2="$(g rev-parse origin/main)"; echo "   M2(origin/main)=$M2 edits a.md line 5"
echo; echo "### 6. Merge link after merging main into the branch (reviewed head F3)"
g merge -q --no-edit origin/main >/dev/null; ( cd "$W" && "$ML" "$A" "$F3" "$M2" ) >"$T/ml-merge.diff"
run "merge link after merge, --verify --base F3" "$T/ml-merge.diff" --verify "$T/prior.md" --base "$F3" --round 3; anc "$F3" F3

echo; echo "### 7. Merge link after a rebase onto main (reviewed head F3, no longer on the branch)"
g checkout -q -b feat-rb "$F3"; g rebase -q origin/main >/dev/null 2>&1; echo "   rebased HEAD: $(g rev-parse HEAD)"
( cd "$W" && "$ML" "$A" "$F3" "$M2" ) >"$T/ml-rb.diff"; echo "   merge link touches: $(grep '^diff --git' "$T/ml-rb.diff" | tr '\n' ' ')"
run "merge link after rebase, --verify --base F3" "$T/ml-rb.diff" --verify "$T/prior.md" --base "$F3" --round 3; anc "$F3" F3; onmain "$F3" F3
echo; echo "### 7w. Wording pass after the rebase: the same delta, --wording-pass --base F3, no --verify"
run "wording pass after rebase, --base F3" "$T/ml-rb.diff" --wording-pass --base "$F3"; anc "$F3" F3; onmain "$F3" F3

echo; echo "### 8. PR targets a non-default branch: --base <merge base with that branch>"
g checkout -q -b release "$A"; printf 'r one\n' >"$W/r.md"; c R1; g push -q origin release
g checkout -q -b feat2 release; printf 'r two\n' >"$W/r.md"; c G1
MB="$(g merge-base origin/release HEAD)"; g diff origin/release...HEAD >"$T/rel.diff"
run "non-default target, --base merge-base" "$T/rel.diff" --base "$MB"; anc "$MB" "merge-base(origin/release)"

echo; echo "### 9. sweep_claims.sh --base origin/main in the misfire's state (not changed by the guard)"
g checkout -q feat; g reset -q --hard "$F1"
g fetch -q origin; ( cd "$W" && "$SW" --base origin/main ) 2>&1 | sed 's/^/   /'; echo "   sweep exit: $?"; anc origin/main origin/main
[ -n "${KEEP:-}" ] && echo "kept $T" || rm -rf "$T"
```

Its output (verbatim; temp paths as printed):
```
command: /bin/bash /private/tmp/claude-501/-Users-matt-Devel-website-builder--claude-worktrees-plan-base-ancestor-guard-4c9cae/d2f71a83-a10b-4cc1-89e4-c097d75c2c1b/scratchpad/base_uses.sh <worktree>/skills/independent-review
run: 2026-11-09T18:46:19Z, git version 2.54.0 (Apple Git-157), independent_review.sh at croftweaver 6859448c, stub codex, REVIEW_LOG=off
A=7b496477fb4cceb9ca3aff1403390f1e021bc0c8 F1=01cec4b56368431d78d56a275bdfa8580eebbca2 M1(origin/main)=b1a99ae085acb45a850906ce1c667187c12cc024

### 1. The misfire: main moved past the branch; two-dot diff, --base origin/main
   two-dot diff touches: diff --git a/a.md b/a.md diff --git a/b.md b/b.md 
== two-dot, --base origin/main
   args: --base origin/main
   script exit: 0
   base: b1a99ae085acb45a850906ce1c667187c12cc024 (--base origin/main)
   is-ancestor origin/main HEAD: exit 1
   is-ancestor origin/main origin/HEAD (origin/main): exit 0

### 1v. The incident's round 5: the same two-dot diff and --base origin/main, in a --verify round
== two-dot, --verify --base origin/main
   args: --verify /private/var/folders/tv/76d0rgkj0451hxz37vkl9mth0000gn/T/base-uses.M5tQ5h/prior.md --base origin/main --round 2
   script exit: 0
   base: b1a99ae085acb45a850906ce1c667187c12cc024 (--base origin/main)
   is-ancestor origin/main HEAD: exit 1
   is-ancestor origin/main origin/HEAD (origin/main): exit 0

### 2. The whole change: three-dot diff, no --base (fetches the bare origin)
== three-dot, no --base
   args: 
   script exit: 0
   base: 7b496477fb4cceb9ca3aff1403390f1e021bc0c8 (merge base with origin's HEAD b1a99ae085acb45a850906ce1c667187c12cc024, fetched; every changed tracked file present)
   is-ancestor merge-base(=A) HEAD: exit 0

### 3. Delta since a reviewed head (F1): --verify --base F1
== delta, --verify --base F1
   args: --verify /private/var/folders/tv/76d0rgkj0451hxz37vkl9mth0000gn/T/base-uses.M5tQ5h/prior.md --base 01cec4b56368431d78d56a275bdfa8580eebbca2 --round 2
   script exit: 0
   base: 01cec4b56368431d78d56a275bdfa8580eebbca2 (--base 01cec4b56368431d78d56a275bdfa8580eebbca2)
   is-ancestor F1 HEAD: exit 0

### 4. Wording pass since the last reviewed head (F2): --wording-pass --base F2
== wording pass, --base F2
   args: --wording-pass --base 0b009a55e2beaff0aad085baab848b8ddeb33cf3
   script exit: 0
   base: 0b009a55e2beaff0aad085baab848b8ddeb33cf3 (--base 0b009a55e2beaff0aad085baab848b8ddeb33cf3)
   is-ancestor F2 HEAD: exit 0

### 5. Working-tree change on top of HEAD: --base HEAD
== working tree, --base HEAD
   args: --base HEAD
   script exit: 0
   base: 9ac54b7bd7a1f6b1af4e74a75628305925e6ea8d (--base HEAD; new sides from the working tree)
   is-ancestor HEAD HEAD: exit 0
   M2(origin/main)=e7e24fe1f489741ddec2cbe73a70cb397936067f edits a.md line 5

### 6. Merge link after merging main into the branch (reviewed head F3)
== merge link after merge, --verify --base F3
   args: --verify /private/var/folders/tv/76d0rgkj0451hxz37vkl9mth0000gn/T/base-uses.M5tQ5h/prior.md --base 9ac54b7bd7a1f6b1af4e74a75628305925e6ea8d --round 3
   script exit: 0
   base: 9ac54b7bd7a1f6b1af4e74a75628305925e6ea8d (--base 9ac54b7bd7a1f6b1af4e74a75628305925e6ea8d)
   is-ancestor F3 HEAD: exit 0

### 7. Merge link after a rebase onto main (reviewed head F3, no longer on the branch)
   rebased HEAD: 69ff428e0b7b7f5c98d83f3ac480b67c2cb776dc
   merge link touches: diff --git a/a.md b/a.md 
== merge link after rebase, --verify --base F3
   args: --verify /private/var/folders/tv/76d0rgkj0451hxz37vkl9mth0000gn/T/base-uses.M5tQ5h/prior.md --base 9ac54b7bd7a1f6b1af4e74a75628305925e6ea8d --round 3
   script exit: 0
   base: 9ac54b7bd7a1f6b1af4e74a75628305925e6ea8d (--base 9ac54b7bd7a1f6b1af4e74a75628305925e6ea8d)
   is-ancestor F3 HEAD: exit 1
   is-ancestor F3 origin/HEAD (origin/main): exit 1

### 7w. Wording pass after the rebase: the same delta, --wording-pass --base F3, no --verify
== wording pass after rebase, --base F3
   args: --wording-pass --base 9ac54b7bd7a1f6b1af4e74a75628305925e6ea8d
   script exit: 0
   base: 9ac54b7bd7a1f6b1af4e74a75628305925e6ea8d (--base 9ac54b7bd7a1f6b1af4e74a75628305925e6ea8d)
   is-ancestor F3 HEAD: exit 1
   is-ancestor F3 origin/HEAD (origin/main): exit 1

### 8. PR targets a non-default branch: --base <merge base with that branch>
== non-default target, --base merge-base
   args: --base ab0f4ffa43f55568060bbbd0cd4494d386c77b8f
   script exit: 0
   base: ab0f4ffa43f55568060bbbd0cd4494d386c77b8f (--base ab0f4ffa43f55568060bbbd0cd4494d386c77b8f)
   is-ancestor merge-base(origin/release) HEAD: exit 0

### 9. sweep_claims.sh --base origin/main in the misfire's state (not changed by the guard)
   sweep_claims: 0 sentences to check in 1 file swept.
   sweep exit: 0
   is-ancestor origin/main HEAD: exit 1
exit 0
```

## READ E2: the incident (session transcript 3ee41cdd, its saved round outputs, and its repository's history)

Read 2026-11-09T16:14:27Z. The project's name is replaced by <project> below.

$ grep -h "^base:" <scratchpad>/r5-r1.md <scratchpad>/r5-r2.md <scratchpad>/r5-r5.md   (round outputs of the R5 gate)
```
r5-r1.md: base: 934bcc12ffc4f799f798e995848fd6d78d642805 (--base origin/main; new sides from the working tree)
r5-r2.md: base: 934bcc12ffc4f799f798e995848fd6d78d642805 (--base origin/main; new sides from the working tree)
r5-r5.md: base: a4934f29f2bb1ae1f2e27ffd8b91c9b91a9e7785 (--base origin/main)
```

Round 5 command (from the transcript, 2026-11-09T09:05:49Z), the review part, --cut text as written:
```
git diff origin/main > $S/r5.diff; ... independent_review.sh $S/r5.diff --diff --base origin/main --depth normal --round 5 --earned-by mac-copy-evidence --cut "dropped the local-snapshot start-date claim; recorded their deletion instead" --verify $S/r5-r4.md --evidence $S/r5-evidence.md > $S/r5-r5.md 2>&1
```

$ grep "^diff --git" <scratchpad>/r5.diff
```
diff --git a/<another-session>/PROPOSAL.md b/power-users/PROPOSAL.md
diff --git a/<this-change>/PLAN-launch-2026-10.md b/security-hardening/PLAN-launch-2026-10.md
```

$ git log --first-parent --format="%h %ad %P %s" --date=iso -5 5dbc8f99   (the branch head after round 5; subjects trimmed)
```
5dbc8f9 2026-11-09 10:05:49 +0100 d80098f26e516574414d061f9b842419f610fc91
d80098f 2026-11-09 09:53:08 +0100 ce1baa661562695d52ceb3d632f889e64f07a1b4 a7617e4840fef9449a2464e9639081bb2c77b219
ce1baa6 2026-11-09 09:53:08 +0100 9d18e07df03cb1b5c4eaded9d4de6c80871e3831
9d18e07 2026-11-09 09:23:11 +0100 934bcc12ffc4f799f798e995848fd6d78d642805
934bcc1 2026-11-09 09:09:00 +0100 b58e4946ebfd02bbc1003a492a8955c08ab29017
```

$ git log --oneline 934bcc12..a4934f29   (subjects dropped)
```
a4934f2
a7617e4
b715400
409298a
7bb7cbe
a1f2d1d
```

```
git merge-base --is-ancestor 934bcc12 5dbc8f99: exit 0
git merge-base --is-ancestor a7617e4 5dbc8f99: exit 0
git merge-base --is-ancestor a4934f29 5dbc8f99: exit 1
```

## READ E3: the base check as it stands (independent_review.sh, croftweaver d0f5c89e, lines 586-700)
```bash
# BASE CHECK (header). Here: after the artifact is read and its type known, before the size check,
# any reviewer, or any of the artifact leaving the machine. Only the default base's fetch goes out
# first, and it sends nothing of the artifact.
BASE_LINE=""
base_refuse() {   # <why> [<what to do> ...]: refuse the run before anything is reviewed
  printf 'Base check: %s\n' "$1" >&2; shift
  [ $# -eq 0 ] || printf '%s\n' "$@" >&2
  exit 2
}
if [ "$TYPE" != diff ]; then
  [ -z "$BASE" ] || base_refuse "--base is for a diff, and this run reviews a $TYPE." "Drop --base, or pass --diff if the artifact is a diff."
elif [ "$BASE" = none ]; then
  BASE_LINE="base: not checked (--base none)"
else
  none_hint="For a diff that did not come from git diff in this repository, pass --base none."
  command -v git >/dev/null 2>&1 || base_refuse "git not found, so the diff cannot be checked." "$none_hint"
  command -v perl >/dev/null 2>&1 || { WHY="perl not found, so the diff cannot be checked."; base_refuse "$WHY" "$none_hint"; }
  top="$(git rev-parse --show-toplevel 2>/dev/null)" && [ -n "$top" ] \
    || base_refuse "not inside a git work tree, so the diff's paths mean nothing here." "Run from the repository the diff came from. $none_hint"
  head_id="$(git -C "$top" rev-parse --verify --quiet 'HEAD^{commit}')" \
    || base_refuse "the repository has no commit at HEAD." "$none_hint"
  # After top is known, so the printed command makes the delta from the repository root with the
  # flags of the mismatch refusal's remedy below, which override prefix, colour, external-diff and
  # textconv config.
  [ -n "$BASE" ] || [ -z "$VERIFY_FILE" ] \
    || base_refuse "a verification round reviews the change since the last reviewed head, so it must name that head." "Pass --base <last-reviewed-head>, with the diff made from that head:" \
         "  git -C $(printf '%q' "$top") diff --no-ext-diff --no-color --no-textconv -M --src-prefix=a/ --dst-prefix=b/ <last-reviewed-head> HEAD -- . ':(exclude)docs/reviews/' | $(printf '%q' "$SCRIPT_DIR/${0##*/}") - --verify $(printf '%q' "$VERIFY_FILE") --base <last-reviewed-head> <your other options>" \
         "After a merge of the base or a rebase, send the merge link instead, with the same --base (SKILL.md step 6):" \
         "  $(printf '%q' "$SCRIPT_DIR/merge_link.sh") <old-merge-base> <last-reviewed-head> <new-merge-base>"
  coverage=0
  if [ -n "$BASE" ]; then
    base_id="$(git -C "$top" rev-parse --verify --quiet "$BASE^{commit}")" \
      || base_refuse "--base $BASE is not a commit in this repository." "Name the commit the diff starts from, or none."
    base_how="--base $BASE"
  else
    coverage=1
    local_tip="$(git -C "$top" rev-parse --verify --quiet 'refs/remotes/origin/HEAD^{commit}')" || local_tip=""
    local_hint="Or name the base: --base <rev>."
    if [ -n "$local_tip" ] && local_base="$(git -C "$top" merge-base "$local_tip" HEAD 2>/dev/null)"; then
      local_hint="To go on with the local origin/HEAD instead: --base $local_base"
    fi
    if [ "$LOCAL_ONLY" = 1 ]; then
      [ -n "$local_tip" ] \
        || base_refuse "--local-only never fetches, and origin/HEAD is not set here, so the base of the whole change is unknown." "Name it: --base <the merge base of HEAD with the default branch>."
      tip="$local_tip"
      base_how="merge base with origin/HEAD $tip, not fetched: --local-only"
    else
      fetch_limit="${REVIEW_FETCH_TIMEOUT:-30}"
      case "$fetch_limit" in
        ''|*[!0-9]*|0*) base_refuse "REVIEW_FETCH_TIMEOUT=\"$fetch_limit\" is not a whole number of seconds from 1 to 600." ;;
      esac
      [ ${#fetch_limit} -le 3 ] && [ "$fetch_limit" -le 600 ] || base_refuse "REVIEW_FETCH_TIMEOUT=\"$fetch_limit\" is over 600 seconds."
      # Bounded the way the site template's git-stand.mjs bounds its own fetch: no prompts, ssh and
      # http give up on a dead or stalled connection by themselves, and the whole fetch has a time
      # limit. GIT_SSH_COMMAND is set only when the person has not chosen an ssh of their own.
      fetch_err="$(
        export GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never
        if [ -z "${GIT_SSH_COMMAND:-}" ] && [ -z "${GIT_SSH:-}" ] && ! git -C "$top" config core.sshCommand >/dev/null 2>&1; then
          export GIT_SSH_COMMAND='ssh -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=10 -o ServerAliveCountMax=2'
        fi
        perl "$PERL_DIR/run_limited.pl" "$fetch_limit" git -C "$top" -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=20 fetch --quiet origin HEAD 2>&1
      )"; fetch_rc=$?
      if [ "$fetch_rc" -eq 142 ]; then
        base_refuse "fetching origin's HEAD did not finish within $fetch_limit seconds, so the base of the whole change is unknown." "$local_hint"
      elif [ "$fetch_rc" -ne 0 ]; then
        base_refuse "fetching origin's HEAD failed (exit $fetch_rc), so the base of the whole change is unknown: ${fetch_err##*$'\n'}" "$local_hint"
      fi
      tip="$(git -C "$top" rev-parse --verify --quiet 'FETCH_HEAD^{commit}')" \
        || base_refuse "the fetch left no FETCH_HEAD to read." "$local_hint"
      base_how="merge base with origin's HEAD $tip, fetched"
    fi
    base_id="$(git -C "$top" merge-base "$tip" HEAD 2>/dev/null)" \
      || base_refuse "HEAD and origin's HEAD ($tip) have no merge base here: a shallow clone, or unrelated histories." "Fetch the history (git fetch --unshallow), or name the base: --base <rev>."
  fi
  bc_out="$(printf '%s\n' "$CONTENT" | perl "$PERL_DIR/diff_headers.pl" "$top" "$base_id" "$head_id" "$coverage" 2>&1)"; bc_rc=$?
  bc_target="" ; bc_left="" ; bc_bad="" ; bc_bad_n=0 ; bc_cont="" ; bc_cont_n=0 ; bc_why="" ; bc_other=""
  while IFS= read -r bc_line; do
    case "$bc_line" in
      target$'\t'*)   bc_target="${bc_line#*$'\t'}" ;;
      left-out$'\t'*) bc_left="${bc_left:+$bc_left, }${bc_line#*$'\t'}" ;;
      mismatch$'\t'*) bc_line="${bc_line#*$'\t'}"; bc_bad="$bc_bad  ${bc_line%%$'\t'*}: ${bc_line#*$'\t'}"$'\n'; bc_bad_n=$((bc_bad_n + 1)) ;;
      content$'\t'*) bc_cont="$bc_cont  ${bc_line#*$'\t'}"$'\n'; bc_cont_n=$((bc_cont_n + 1)) ;;
      refuse$'\t'*|error$'\t'*) bc_why="${bc_line#*$'\t'}" ;;
      '') ;;
      *) bc_other="${bc_other:+$bc_other; }$bc_line" ;;
    esac
  done <<<"$bc_out"
  remedy_revs="$base_id HEAD"
  [ "$bc_target" = "the working tree" ] && remedy_revs="$base_id"
  # A record marked binary whose new side git shows as text is git -M's own rename of a binary file
  # to a text one, or a hand edit: with no renames, git writes the text side's lines.
  remedy_renames="-M"
  case "$bc_bad" in *": the diff marks it binary, but git shows its content"*) remedy_renames="--no-renames" ;; esac
  remedy="git -C $(printf '%q' "$top") diff --no-ext-diff --no-color --no-textconv $remedy_renames --src-prefix=a/ --dst-prefix=b/ $remedy_revs -- . ':(exclude)docs/reviews/'"
  case $bc_rc in
    0)
      BASE_LINE="base: $base_id ($base_how"
      [ "$bc_target" = "the working tree" ] && BASE_LINE="$BASE_LINE; new sides from the working tree"
      if [ "$coverage" = 1 ]; then
        if [ -n "$bc_left" ]; then BASE_LINE="$BASE_LINE; not in this diff: $bc_left"
        else BASE_LINE="$BASE_LINE; every changed tracked file present"; fi
      fi
      BASE_LINE="$BASE_LINE)" ;;
    1)
      bc_with="$bc_target"; [ "$bc_with" = HEAD ] && bc_with="HEAD $head_id"
      base_refuse "$bc_bad_n file side(s) in this diff do not match its base, so it is not reviewed." \
        "  base: $base_id ($base_how)" "  new sides compared with: $bc_with" "${bc_bad%$'\n'}" \
        "Make the diff again from that base:" "  $remedy" "For a delta since a reviewed head, pass --base <that head>." ;;
    3)
      case "$bc_why" in
        "no diff --git record"*) base_refuse "this diff cannot be checked: $bc_why." "$none_hint" ;;
        *) base_refuse "this diff cannot be checked: $bc_why." "Make it with git: $remedy" "$none_hint" ;;
      esac ;;
    5) base_refuse "git sees no change from the base ($base_id) to HEAD or to the working tree, so there is nothing to review against it." "Name the commit the diff starts from: --base <rev>." ;;
    6) base_refuse "its headers match the base, but its hunks do not apply to it: $bc_why." \
```

## READ E4: SKILL.md lines 141-151 and 263-276 (croftweaver d0f5c89e)
```
   or an Antigravity seat. A DIFF artifact is the change without the trail:
   `git diff <base>...HEAD -- . ':(exclude)docs/reviews/'` (the trail still ships in the PR;
   reviewers auditing it cost rounds). Run from the repository the diff came from: before
   anything is sent, the script checks the diff against git (BASE CHECK in its header). With no
   `--base` it fetches origin's HEAD and checks the diff against the whole change from the merge
   base: every file's sides, and that its hunks give HEAD's content (or, for uncommitted work,
   the working tree's); a diff that fails is
   refused, naming each file and the command that makes a correct one. Any other diff (a delta,
   a merge link, the wording pass) passes `--base <the commit it starts from>`; so does a change
   whose PR targets a branch other than the default one (`--base <its merge base with that
   branch>`). A diff not made by `git diff` in this repository passes `--base none`. Evidence for
...
   pass. A refuted BUG gets no reviewer's second look this way, so name it to the owner with its
   evidence before the gate closes (step 8).
   - **Artifact.** DIFF: `git diff <last-reviewed-head>..HEAD -- . ':(exclude)docs/reviews/'`,
     sent with `--base <last-reviewed-head>` (a `--verify` round on a diff is refused without it).
     After a merge of the base or a rebase, the **merge link** instead, not a full round: what
     changed in the change's own files since the last review, merge effects included, plus any
     file the merge changed that the change's code calls directly, when known:

     ```
     scripts/merge_link.sh <old-merge-base> <last-reviewed-head> <new-merge-base> [-- <path>...]
     ```

     Its diff starts from the last reviewed head too: send it with `--base <last-reviewed-head>`.

```
