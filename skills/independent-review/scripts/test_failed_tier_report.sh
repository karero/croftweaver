#!/usr/bin/env bash
#
# test_failed_tier_report.sh — drives independent_review.sh end to end, the way a
# caller does (default flags, auto-detected ollama model), with stub `codex` and
# `ollama` CLIs first on PATH and $HOME relocated. No reviewer is contacted and
# nothing leaves the machine; Antigravity is forced off except in case 23, which
# turns it on against a stub `agy`.
#
# Why it exists: on 2026-09-11 the ollama-cloud tier hit its weekly quota (HTTP
# 429). The error sat only in a temp .err file, stdout carried the codex section
# alone, and the exit was 0 — so a one-reviewer round read as a clean pair. These
# cases pin that every attempted tier shows up on stdout, that the closing
# "reviewers:" line tells a quota refusal from a config failure (the remedies
# differ), and that the exit-code contract (0 = at least one gate-eligible
# reviewer, 4 = none) is unchanged.
#
# Usage: bash skills/independent-review/scripts/test_failed_tier_report.sh
set -u
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
SCRIPT="$HERE/independent_review.sh"
T="$(mktemp -d "${TMPDIR:-/tmp}/ir-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin" "$T/u/.codex"
: >"$T/u/.codex/auth.json"
printf 'model = "stub-codex"\n' >"$T/u/.codex/config.toml"
printf 'diff --git a/x b/x\n+retry on HTTP 429 after a pause\n' >"$T/change.diff"
printf '# Plan\n\nStep 1: do the thing.\n' >"$T/plan.md"
# Built at runtime: check_model_agnostic.sh flags any literal "<word>:cloud" in this skill.
STUB_TAG="stub-model"; STUB_TAG="${STUB_TAG}:cloud"

# Stubs are plain sh with printf '%s\n' so they behave the same under dash (CI) and bash.
cat >"$T/bin/codex" <<'EOF'
#!/bin/sh
: >"$STUB_MARKS/codex-ran"
# The API keys are unset for every seat but their own (#165): codex must never see them.
[ -n "${MELIOUS_API_KEY:-}" ] && : >"$STUB_MARKS/codex-saw-melious-key"
[ -n "${OLLAMA_API_KEY:-}" ] && : >"$STUB_MARKS/codex-saw-ollama-key"
# Like the real CLI (0.157.0, seen 2026-09-26): outside a git repo, refuse to start
# unless --skip-git-repo-check is passed. Records its whole argv, the prompt replaced by
# <prompt> (found by its content, not its position), so a test can pin it exactly: an
# added sandbox override fails the match instead of hiding behind "-s read-only is in
# there somewhere" (round 1, fresh-eyes), and so does one placed after the prompt or
# after a prompt moved to stdin (round 2, fresh-eyes and ollama). Each argument is
# bracketed, so "-s read-only" passed as ONE argument does not match (round 3, fresh-eyes).
skip=0 argv=
for a; do
  [ "$a" = --skip-git-repo-check ] && skip=1
  case "$a" in *'--- BEGIN '*) printf '%s\n' "$a" >"$STUB_MARKS/codex-prompt"; a='<prompt>' ;; esac
  argv="$argv[$a]"
done
printf 'argv=%s cwd=%s git=%s\n' "$argv" "$(pwd -P)" \
  "$(git rev-parse --is-inside-work-tree 2>/dev/null || echo no)" >"$STUB_MARKS/codex-args"
if [ $skip -eq 0 ] && ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  printf '%s\n' 'Reading additional input from stdin...' \
    'Not inside a trusted directory and --skip-git-repo-check was not specified.' >&2
  exit 1
fi
case "${CODEX_STUB:-ok}" in
  ok)   printf '%s\n' '- BUG: stub finding one' '- NIT: stub finding two' ;;
  auth) # codex echoes the reviewed artifact into stderr — here one that mentions
        # a 429 — long before its real, non-quota error.
        printf '%s\n' 'user' '+retry on HTTP 429 Too Many Requests after a pause' >&2
        i=0; while [ $i -lt 20 ]; do echo "exec step $i" >&2; i=$((i+1)); done
        echo "ERROR: not signed in - run codex login" >&2; exit 1 ;;
  authshort) # the same, with the artifact line right next to the error
        printf '%s\n' 'user' '+retry on HTTP 429 Too Many Requests after a pause' >&2
        echo "ERROR: not signed in - run codex login" >&2; exit 1 ;;
  authctx) # a diff CONTEXT line (leading space) shaped like an error, then the real one
        printf '%s\n' 'user' ' ERROR: 429 Too Many Requests in the old handler' >&2
        echo "ERROR: not signed in - run codex login" >&2; exit 1 ;;
  tracing429) # a tracing-style error line followed by trailer lines. The shape is
        # assumed, not captured from a real codex quota refusal.
        printf '%s\n' '2026-09-11T19:24:25.123Z ERROR codex_core::client: unexpected status 429 Too Many Requests' \
          'tokens used' '0' 'session end' 'bye' >&2; exit 1 ;;
  diskquota) # a local setup failure that merely contains the word "quota"
        echo "ERROR: disk quota exceeded while writing the session log" >&2; exit 1 ;;
  reply) printf '%s\n' "$STUB_REPLY" ;;   # a successful run whose whole reply is $STUB_REPLY
  meet)  # a reviewer that waits (30s or more) to see ollama start, and notes if it did: run
         # side by side, each sees the other; one after the other, the first never can
         i=0; while [ ! -e "$STUB_MARKS/ollama-ran" ] && [ $i -lt 300 ]; do sleep 0.1; i=$((i+1)); done
         [ -e "$STUB_MARKS/ollama-ran" ] && : >"$STUB_MARKS/codex-saw-ollama"
         printf '%s\n' '- BUG: stub finding one' ;;
  slow)  sleep 2; printf '%s\n' '- BUG: stub finding one' ;;   # a reviewer that takes a while
  waitmelious) # finishes only once Melious has started (10s cap), then marks itself done
        i=0; while [ ! -e "$STUB_MARKS/melious-started" ] && [ $i -lt 100 ]; do sleep 0.1; i=$((i+1)); done
        : >"$STUB_MARKS/codex-done"; printf '%s\n' '- BUG: stub finding one' ;;
  tokens) # a run that reports its token count on stderr, as codex ends a run
        printf '%s\n' 'tokens used' '61,108' >&2; printf '%s\n' '- BUG: stub finding one' ;;
  stubborn) # a CLI that ignores SIGTERM, as one mid-request might; records its pid
        trap '' TERM; echo $$ >"$STUB_MARKS/codex-pid"; sleep 30 ;;
  wrapped) # a launcher whose worker, one level further down, ignores SIGTERM; records its pid
        sh -c 'trap "" TERM; echo $$ >"$STUB_MARKS/codex-worker"; sleep 30' & wait ;;
esac
EOF
cat >"$T/bin/ollama" <<'EOF'
#!/bin/sh
case "$1" in
  list) if [ "${OLLAMA_STUB:-ok}" = listfail ]; then
          echo "Error: could not connect to ollama app, is it running?" >&2; exit 1
        fi
        printf 'NAME                ID      SIZE    MODIFIED\n%s    abc123  -       1 day ago\n' "$STUB_TAG"; exit 0 ;;
  run)  shift
        if [ "$1" = --help ]; then   # STUB_OLDCLI: 1 = too old to know --hidethinking; failhelp =
                                      # help fails; longword = the flag only inside a longer word
          case "${STUB_OLDCLI:-}" in
            1)        echo '      --verbose                 Show timings for response' ;;
            failhelp) echo 'Error: unknown flag: --hidethinking' >&2; exit 1 ;;
            longword) echo '      --hidethinking-format     (a different option)' ;;
            *)        echo '      --hidethinking            Hide thinking output (if provided)' ;;
          esac
          exit 0
        fi
        if [ "$1" = --hidethinking ]; then : >"$STUB_MARKS/ollama-hidethinking"; shift; fi
        : >"$STUB_MARKS/ollama-ran"; printf '%s\n' "$1" >"$STUB_MARKS/ollama-model"
        [ -n "${OLLAMA_API_KEY:-}" ] && printf '%s\n' "$OLLAMA_API_KEY" >"$STUB_MARKS/ollama-cli-key"
        printf '%s\n' "$2" >"$STUB_MARKS/ollama-prompt" ;;
esac
case "${OLLAMA_STUB:-ok}" in
  ok)     printf '%s\n' '- RISK: stub ollama finding' '- NIT: another' ;;
  stubborn) # ignores SIGTERM, as a CLI mid-request might; records its pid
          trap '' TERM; echo $$ >"$STUB_MARKS/ollama-pid"; sleep 30; : >"$STUB_MARKS/ollama-slept" ;;
  think)  # a reasoning model, as the real CLI prints it: the trace only without --hidethinking.
          # Its trace quotes the prompt's "could not read" advice (2026-09-27).
          if [ ! -e "$STUB_MARKS/ollama-hidethinking" ]; then
            printf '%s\n' 'Thinking...' 'The advice says: phrase it about the claim, not "I could not read".' '...done thinking.' ''
          fi
          printf '%s\n' 'RISK — retry.rb:12 — the retry loop never terminates on a stalled connection.' 'No BUG or NIT findings.' ;;
  429)    # the byte shape of the 2026-09-11 failure: spinner, cursor and sync-mode escapes
          printf '\033[?2026h\033[?25l\033[1G\342\240\231 \033[K\033[?25h\033[?2026l\033[?25l\033[2K\033[1G\033[?25hError: 429 Too Many Requests: you (someone) have reached your weekly usage limit, upgrade for higher limits\n' >&2
          exit 1 ;;
  out429) printf '%s\n' 'Error: 429 Too Many Requests: weekly usage limit reached'; exit 1 ;;
  badtag) i=0; while [ $i -lt 4 ]; do printf '\033[?25l\033[1Gpulling manifest \342\240\213 \033[K\033[?25h' >&2; i=$((i+1)); done
          printf '\nError: pull model manifest: file does not exist\n' >&2; exit 1 ;;
  oddesc) # escapes outside the ESC[...letter shape: ESC[0~ (final byte ~), a charset
          # designation ESC(B, and a BEL
          printf '\033[0~\033[2;5H\033(BError: bad model\007\n' >&2; exit 1 ;;
  oddbody) # a review body with an escape the redraw filter does not emulate
          printf 'Introduction\n\033[0~1. BUG: important finding\n- NIT: second finding\n' ;;
  strayesc) # a review body ending in a lone ESC the filter cannot parse
          printf '%s\n' '- BUG: one' '- NIT: two'; printf '\033' ;;
  utf8cut) # stderr starting mid-glyph, as `tail -c` produces: two continuation bytes
          printf '\240\231 spinner\nError: 429 Too Many Requests: weekly usage limit reached\n' >&2; exit 1 ;;
  bigquota) # the quota error first, then ~120 KB of other error-shaped lines across stderr
          # and stdout, each line distinct (the quote collapses repeats): past the pipe
          # buffer, so a grep -q that stops at the 429 exits early
          x=$(printf '%8100s' '' | tr ' ' x)
          printf '%s\n' 'Error: 429 Too Many Requests: weekly usage limit reached' >&2
          i=0; while [ $i -lt 7 ]; do printf 'Error: stream %s failed %s\n' "$i" "$x" >&2; i=$((i+1)); done
          i=0; while [ $i -lt 8 ]; do printf 'Error: stream 1%s failed %s\n' "$i" "$x"; i=$((i+1)); done
          exit 1 ;;
  notreview) # a reply the refusal check rejects, carrying a decoy error-shaped 429 line
          printf '%s\n' 'No findings.' 'I could not read the retry code.' \
            'Error: 429 responses are retried, per the comment - UNVERIFIABLE.' ;;
  reply)  printf '%s\n' "$STUB_REPLY" ;;   # as in the codex stub: the whole reply is $STUB_REPLY
  slow)   sleep 2; printf '%s\n' '- RISK: stub ollama finding' ;;
  meet)   # as in the codex stub, the other way round
          i=0; while [ ! -e "$STUB_MARKS/codex-ran" ] && [ $i -lt 300 ]; do sleep 0.1; i=$((i+1)); done
          [ -e "$STUB_MARKS/codex-ran" ] && : >"$STUB_MARKS/ollama-saw-codex"
          printf '%s\n' '- RISK: stub ollama finding' ;;
esac
EOF
cat >"$T/bin/agy" <<'EOF'
#!/bin/sh
# Records its argv as the codex stub does, prompt replaced by <prompt>, and keeps the
# prompt itself so a test can check WHICH prompt was sent, not just that one was.
argv=
for a; do
  case "$a" in *'--- BEGIN '*) printf '%s\n' "$a" >"$STUB_MARKS/agy-prompt"; a='<prompt>' ;; esac
  argv="$argv[$a]"
done
printf 'argv=%s\n' "$argv" >"$STUB_MARKS/agy-args"
printf '%s\n' "$(pwd -P)" >"$STUB_MARKS/agy-cwd"
ls -A | wc -l | tr -d ' ' >"$STUB_MARKS/agy-cwd-entries"
case "${AGY_STUB:-ok}" in
  ok)     printf '%s\n' '- BUG: stub agy finding' '- NIT: another' ;;
  denied) # the 2026-09-26 failure: exit 0, nothing on stdout, the reason on stderr
          printf '%s\n' 'jetski: no output produced — a tool required the "command" permission that headless mode cannot prompt for, so it was auto-denied.' >&2 ;;
esac
EOF
# A stub curl for the ollama HTTP API transport and the Melious seat: records the URL, the request
# body and the headers it was handed in a file (ollama) or on stdin (Melious) — never argv, which
# must carry no key — and plays back a canned NDJSON stream (ollama) or SSE stream (Melious).
cat >"$T/bin/curl" <<'EOF'
#!/bin/sh
out= body= url= ARGV0="$*"
while [ $# -gt 0 ]; do
  case "$1" in
    -o) out="$2"; shift ;;
    --data-binary) body="${2#@}"; shift ;;
    -H) case "$2" in @-) cat >"$STUB_MARKS/curl-hdr"; : >"$STUB_MARKS/curl-hdr-stdin" ;; @*) cp "${2#@}" "$STUB_MARKS/curl-hdr" 2>/dev/null ;; esac; shift ;;
    -w|--max-time) shift ;;
    http*) url="$1" ;;
  esac
  shift
done
printf '%s\n' "$ARGV0" >"$STUB_MARKS/curl-argv-any"
# Is the key anywhere on disk while the call is in flight (an interrupt here would leave it)?
if [ -n "${STUB_KEY:-}" ] && grep -rqF -- "$STUB_KEY" "$REVIEW_RAW_DIR" 2>/dev/null; then : >"$STUB_MARKS/key-on-disk"; fi
case "$url" in
  https://api.melious.ai/*|*/chat/completions)   # the Melious seat: an OpenAI-style SSE stream
    printf '%s\n' "$url" >"$STUB_MARKS/melious-url"
    cp "$body" "$STUB_MARKS/melious-body"
    # The marker this run asked for (new each run; the ask is last, after the reviewed text); canned
    # replies say @@MARK@@ where it goes.
    M="$(perl -MJSON::PP -0777 -ne 'my $j = decode_json($_); print $1 if $j->{messages}[0]{content} =~ /.*holds exactly (=== FINAL REVIEW \S+ ===)/s' "$body")"
    [ -e "$STUB_MARKS/curl-hdr" ] && mv "$STUB_MARKS/curl-hdr" "$STUB_MARKS/melious-hdr"
    [ -e "$STUB_MARKS/curl-hdr-stdin" ] && mv "$STUB_MARKS/curl-hdr-stdin" "$STUB_MARKS/melious-hdr-stdin"
    d() { printf 'data: {"choices":[{"index":0,"delta":{%s},"finish_reason":%s}],"usage":%s}\n\n' "$1" "$2" "${3:-null}"; }
    case "${MELIOUS_STUB:-ok}" in
      ok)     { d '"reasoning_content":"Thinking: I could not read the file."' null
                d '"content":"- BUG: melious "' null
                d '"content":"finding one\n- NIT: two"' null
                d '"content":null' '"stop"'
                d '"content":null' null '{"prompt_tokens":400,"completion_tokens":200,"total_tokens":600}'
                printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      429)    printf '%s\n' '{"error":{"message":"Rate limit exceeded for your plan","code":"rate_limited"}}' >"$out"; printf 429 ;;
      trunc)  d '"content":"- BUG: cut off"' null >"$out"; printf 200 ;;
      length) { d '"content":"- BUG: cut off"' null; d '"content":null' '"length"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      inlinethink) # a trace inlined in content; alone it would reject the one-finding review.
              # Tags built at runtime: literal ones in this repo's files made the provider end a
              # reviewer's reasoning at a quoted closing tag (#165).
              TO="<""think>"; TC="</""think>"
              { d "\"content\":\"${TO}I could not read the file.${TC}\\n\"" null
                d '"content":"- RISK: inline finding"' '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      miderr) { d '"content":"- BUG: partial"' null
                printf 'data: {"error":{"message":"upstream overloaded"}}\n\n'; } >"$out"; printf 200 ;;
      notstream) # a whole, pretty-printed reply well past 4 KB, as a real review would be
              { printf '{\n  "choices": [ {\n    "message": { "content": "'
                printf -- '- RISK: retry on HTTP 429 Too Many Requests, a rate limit\\n'
                i=0; while [ $i -lt 120 ]; do printf -- '- NIT: finding number %s of a long review\\n' "$i"; i=$((i+1)); done
                printf '" },\n    "finish_reason": "stop"\n  } ]\n}\n'; } >"$out"; printf 200 ;;
      down)   echo "curl: (56) CONNECT tunnel failed, response 403" >&2; exit 56 ;;
      # Part of a reply, then the connection breaks (#165: a runaway reply reset after 38 minutes).
      reset)  d '"content":"- BUG: half a reply"' null >"$out"
              echo "curl: (56) Recv failure: Connection reset by peer" >&2; exit 56 ;;
      filter) { d '"content":"- BUG: half a finding\n- NIT: two"' null; d '"content":null' '"content_filter"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      nousage) { d '"content":"- BUG: second run\n- NIT: two"' '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      thinkonly) { d '"reasoning_content":"long thoughts"' null; d '"content":null' '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      thinklast) TO="<""think>"; TC="</""think>"
              { d "\"content\":\"- BUG: kept before\\n- NIT: two\\n${TO}trailing thoughts${TC}\"" '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      unclosed) TO="<""think>"
              { d "\"content\":\"- BUG: kept first\\n- NIT: two\\n${TO}unfinished, I could not read it\"" '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      # Reasoning leaked into the reply (#165): the trace mentions the marker inline and once as a
      # line of its own (a draft), then the real marker line and the answer.
      leak|leaknofull)
              [ "$MELIOUS_STUB" = leaknofull ] && mkdir -p "$REVIEW_RAW_DIR/melious.full"   # after the startup purge
              { d '"content":"Let me think. I will write @@MARK@@ before the answer.\n@@MARK@@\n- BUG: draft finding, superseded\nMore thinking about the retry loop.\n"' null
                d '"content":"@@MARK@@\n- BUG: the real finding\n- NIT: two"' '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      bignomark) x=$(printf '%70000s' '' | tr ' ' x)
              { d "\"content\":\"$x\\n- BUG: at the end\\n- NIT: two\"" '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      markdup) { d '"content":"Thinking about it at length.\n@@MARK@@\n- BUG: kept finding\n- NIT: two\n@@MARK@@\n"' '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      markfence) { d '"content":"Thinking first.\n@@MARK@@\n- RISK: fenced case kept\n- NIT: the seat asks for this line:\n```\n@@MARK@@\n```\n"' '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      markwrap) { d '"content":"Reasoning that leaked.\n**@@MARK@@**\n- BUG: wrapped marker kept\n- NIT: two"' '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      bigmarkend) x=$(printf '%70000s' '' | tr ' ' x)
              { d "\"content\":\"$x\\n- BUG: at the end\\n- NIT: two\\n@@MARK@@\\n\"" '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      glued)  { d '"content":"Thinking it over at length, then the answer.@@MARK@@\n- BUG: the real finding\n- NIT: two"' '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      oldmark) { d '"content":"=== FINAL REVIEW ===\n- BUG: a draft that quotes the old fixed marker\n@@MARK@@\n- BUG: the real finding\n- NIT: two\n=== FINAL REVIEW ===\n- NIT: quoted after the review"' '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      quotemark) { d '"content":"@@MARK@@\n- BUG: real finding one\n- NIT: the prompt asks for a line holding exactly `@@MARK@@`\n- NIT: three"' '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      echoglued) { d '"content":"The ask says to write\n@@MARK@@\nthen the findings, BUG/RISK/NIT.\nMore reasoning, then the answer.@@MARK@@\n- BUG: the real finding\n- NIT: two"' '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      fencequote) { d '"content":"@@MARK@@\n- BUG: real finding one\n- NIT: the seat asks for\n  ```\n  @@MARK@@\n  ```\n- NIT: three"' '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      afterfence) { d '"content":"The ask says to write\n@@MARK@@\nthen the findings, BUG/RISK/NIT. A sketch:\n```\nx = 1\n```\n@@MARK@@\n- BUG: the real finding"' '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      indentquote) { d '"content":"@@MARK@@\n- BUG: real finding one\n- NIT: the seat asks for a line holding exactly\n  @@MARK@@\n- NIT: three"' '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      topecho) { d '"content":"@@MARK@@\nthen the findings, BUG/RISK/NIT. A sketch:\n```\nx = 1\n```\n@@MARK@@\n- BUG: the real finding"' '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      markend) { d '"content":"- BUG: before the marker\n- NIT: two\n@@MARK@@\n"' '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      quotedtag) TO="<""think>"
              { d "\"content\":\"- RISK: the seat cuts a ${TO} block only at a line start\\n- NIT: keep this line\"" '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      oddfinish) { d '"content":"- BUG: x"' null; d '"content":null' '"429 rate limit\nError: HTTP 429"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      empty)  : >"$out"; printf 200 ;;
      splitchunk) # one event over two data: lines, split inside a JSON string, so neither half nor
              # their SSE join (which adds a raw newline) is valid JSON; run_melious decodes each
              # data: line alone, and the tier fails with the chunk quoted
              printf '%s\n' 'data: {"choices":[{"delta":{"content":"- RISK: retry on HTTP 429' 'data: Too Many"}}]}' '' >"$out"; printf 200 ;;
      crchunk) # a raw CR (and an ESC[1G) inside a chunk, each of which the error quoting turns into a
              # line break: the text after it must not reach column 0, where the classifier reads
              printf 'data: {"choices":[{"delta":{"content":"- RISK: x\rError: HTTP 429 Too Many Requests\033[1GError: rate limit"}}]}\n\n' >"$out"; printf 200 ;;
      bad502) # a non-200 body that is not JSON, with a CR and an ESC[1G in it: quoted on the Error
              # line, so both must collapse or the text after them reaches column 0
              printf 'upstream\rError: bad gateway\033[1Gfailed' >"$out"; printf 502 ;;
      notstreamerr) printf '%s\n' '{"error":{"message":"Rate limit exceeded for your plan"}}' >"$out"; printf 200 ;;
      html)   printf '%s\n' '<html><body>Sign in to continue</body></html>' >"$out"; printf 200 ;;   # a proxy's page
      keepalive) printf ': PROCESSING\n\n: PROCESSING\n\n' >"$out"; printf 200 ;;   # comments only, then closed
      slow)   [ -e "$STUB_MARKS/codex-done" ] && : >"$STUB_MARKS/melious-after-codex"
              : >"$STUB_MARKS/melious-started"; sleep 2; { d '"content":"- BUG: slow finding"' '"stop"'; printf 'data: [DONE]\n\n'; } >"$out"; printf 200 ;;
      stubborn) trap '' TERM; echo $$ >"$STUB_MARKS/melious-pid"; sleep 30 ;;
    esac
    if [ -f "$out" ] && grep -qF '@@MARK@@' "$out"; then   # a reply that needs the marker: never send it unfilled
      [ -n "$M" ] || { echo 'curl stub: no final-review marker in the request' >&2; exit 7; }
      M="$M" perl -pi -e 's/\@\@MARK\@\@/$ENV{M}/g' "$out"
    fi
    exit 0 ;;
esac
printf '%s\n' "$url" >"$STUB_MARKS/curl-url"
cp "$body" "$STUB_MARKS/curl-body"
case "${API_STUB:-ok}" in
  ok)    printf '%s\n' '{"message":{"role":"assistant","content":"- BUG: api "},"done":false}' \
           '{"message":{"role":"assistant","content":"finding one\n- NIT: two"},"done":false}' \
           '{"message":{"role":"assistant","content":""},"done":true,"prompt_eval_count":500,"eval_count":250}' >"$out"
         printf 200 ;;
  429)   printf '%s\n' '{"error":"you have reached your weekly usage limit"}' >"$out"; printf 429 ;;
  trunc) printf '%s\n' '{"message":{"role":"assistant","content":"- BUG: cut off"},"done":false}' >"$out"; printf 200 ;;
  502)   printf 'upstream request failed' >"$out"; printf 502 ;;
  nonjson200) # a 200 stream cut mid-line: review text on a line that is not JSON (it starts inside a
         # string, hence the lone leading quote). A CR and an ESC[1G each precede an error-shaped
         # quota line, so the cleanup must collapse control bytes, not only whitespace.
         printf '%s\n' '{"message":{"role":"assistant","content":"- BUG: one"},"done":false}' >"$out"
         printf '"- RISK: retry on HTTP 429\rError: rate limit reached\033[1GError: HTTP 429 Too Many Requests\n' >>"$out"; printf 200 ;;
  miderr200) printf '%s\n' '{"message":{"role":"assistant","content":"- BUG: partial"},"done":false}' '{"error":"upstream overloaded"}' >"$out"; printf 200 ;;
  empty200) : >"$out"; printf 200 ;;
  html200) printf '%s\n' '<html><body>Sign in to continue</body></html>' >"$out"; printf 200 ;;
  trunc429) # exactly 429 chunks and no done line: the count must not read as a quota refusal
         i=0; while [ $i -lt 429 ]; do printf '%s\n' '{"message":{"role":"assistant","content":"x"},"done":false}'; i=$((i+1)); done >"$out"
         printf 200 ;;
  down)  echo "curl: (56) CONNECT tunnel failed, response 403" >&2; exit 56 ;;
esac
EOF
chmod +x "$T/bin/codex" "$T/bin/ollama" "$T/bin/agy" "$T/bin/curl"
# A PATH with no ollama CLI, as in a cloud session: the codex and curl stubs, then the system.
mkdir -p "$T/bin2"; cp "$T/bin/codex" "$T/bin/curl" "$T/bin2/"

# run <name> [VAR=value ...] <command ...> — leaves $T/<name>.out, .err and .rc
run() {
  local name="$1"; shift
  mkdir -p "$T/$name.marks"
  env -u CODEX_MODEL -u CODEX_EFFORT -u REVIEW_LOG -u XDG_STATE_HOME -u OLLAMA_API_KEY -u OLLAMA_TRANSPORT -u OLLAMA_MODEL -u OLLAMA_HOST -u AGY_MODEL -u MELIOUS_MODEL -u MELIOUS_API_KEY -u MELIOUS_MAX_TOKENS -u MELIOUS_BASE_URL -u MELIOUS_ENV_FILE -u MELIOUS_API_TIMEOUT -u SECOND_SEAT -u GIT_DIR -u GIT_WORK_TREE \
    PATH="$T/bin:$PATH" HOME="$T/u" WITH_ANTIGRAVITY=0 \
    REVIEW_RAW_DIR="$T/$name.raw" STUB_MARKS="$T/$name.marks" STUB_TAG="$STUB_TAG" "$@" \
    >"$T/$name.out" 2>"$T/$name.err"
  echo $? >"$T/$name.rc"
}
fails=0
check() {   # check <description> <command ...>
  if "${@:2}"; then printf 'ok   %s\n' "$1"; else printf 'FAIL %s\n' "$1"; fails=$((fails+1)); fi
}
has()   { grep -qF -- "$2" "$T/$1"; }
lacks() { ! grep -qF -- "$2" "$T/$1"; }
not_in() { [ -e "$1" ] && ! grep -qF -- "$2" "$1"; }   # not_in <path> <text>: file exists, text absent
rc_is() { [ "$(cat "$T/$1.rc")" = "$2" ]; }

# 1. The incident itself: codex answers, ollama-cloud is refused with a 429.
run incident CODEX_STUB=ok OLLAMA_STUB=429 bash "$SCRIPT" "$T/change.diff"
check "incident: exit stays 0 (one gate-eligible reviewer succeeded)" rc_is incident 0
check "incident: the codex review is still printed" has incident.out "## Independent review — codex (stub-codex, read-only)"
check "incident: the failed tier gets its own section on stdout" has incident.out "## Independent review — ollama-cloud — FAILED"
check "incident: the section quotes the tier's error" has incident.out "Error: 429 Too Many Requests"
check "incident: no terminal escape bytes reach stdout" lacks incident.out $'\033'
check "incident: no spinner glyphs reach stdout" lacks incident.out '⠙'
check "incident: summary names the quota failure" has incident.out "reviewers: codex OK, ollama-cloud FAILED (exit 1; quota/rate limit: wait or add credits)"
check "incident: a DIFF round with 1 reviewer says so" has incident.out "⚠ DIFF round landed with 1 reviewer(s) counted toward the gate"
check "incident: the summary also reaches stderr" has incident.err "reviewers: codex OK, ollama-cloud FAILED (exit 1; quota"

# 2. The normal pair: both reviews, no FAILED section, no degraded note.
run pair bash "$SCRIPT" "$T/change.diff"
check "pair: exit 0" rc_is pair 0
check "pair: codex section" has pair.out "## Independent review — codex (stub-codex, read-only)"
check "pair: ollama section, header unchanged" has pair.out "## Independent review — ollama ($STUB_TAG)"
check "pair: no FAILED section" lacks pair.out "FAILED"
check "pair: summary lists both OK" has pair.out "reviewers: codex OK, ollama-cloud OK"
check "pair: no fewer-than-2 note" lacks pair.out "fewer than the 2"

# 3. A config failure (bad model tag) is NOT reported as a quota problem.
run badtag CODEX_STUB=ok OLLAMA_STUB=badtag bash "$SCRIPT" "$T/change.diff"
check "badtag: FAILED section" has badtag.out "## Independent review — ollama-cloud — FAILED"
check "badtag: quotes the real error line" has badtag.out "Error: pull model manifest: file does not exist"
check "badtag: summary says exit 1, not quota" has badtag.out "reviewers: codex OK, ollama-cloud FAILED (exit 1)"
check "badtag: not classified as quota anywhere" lacks badtag.out "quota/rate limit"
check "badtag: spinner redraws collapse to one line" [ "$(grep -c 'pulling manifest' "$T/badtag.out")" = 1 ]

# 4. Only error-record lines decide quota: codex echoes the reviewed diff (which
#    mentions a 429) into stderr before its real, non-quota error — far from it (4)
#    and right next to it (4b; round-1 review, Codex).
run codexauth CODEX_STUB=auth bash "$SCRIPT" "$T/change.diff"
check "codexauth: exit 0 (ollama-cloud succeeded)" rc_is codexauth 0
check "codexauth: codex FAILED section" has codexauth.out "## Independent review — codex — FAILED"
check "codexauth: quotes the real error" has codexauth.out "not signed in"
check "codexauth: a 429 in the echoed artifact is not read as quota" has codexauth.out "reviewers: codex FAILED (exit 1), ollama-cloud OK"
run codexshort CODEX_STUB=authshort bash "$SCRIPT" "$T/change.diff"
check "codexshort: the 429 line sits inside the quoted tail" has codexshort.out "+retry on HTTP 429 Too Many Requests"
check "codexshort: and still is not read as quota" has codexshort.out "reviewers: codex FAILED (exit 1), ollama-cloud OK"

# 5. Nothing succeeds: exit 4, both failures on stdout, paste prompt still printed.
run none CODEX_STUB=auth OLLAMA_STUB=429 bash "$SCRIPT" "$T/change.diff"
check "none: exit 4" rc_is none 4
check "none: codex FAILED section" has none.out "## Independent review — codex — FAILED"
check "none: ollama FAILED section" has none.out "## Independent review — ollama-cloud — FAILED"
check "none: summary tells the two failures apart" has none.out "reviewers: codex FAILED (exit 1), ollama-cloud FAILED (exit 1; quota/rate limit"
check "none: note says 0 reviewers" has none.out "landed with 0 reviewer(s) counted toward the gate"
check "none: manual paste prompt still printed" has none.out "--- BEGIN diff ---"

# 6. --first-success on a plan: one reviewer by choice — said, not hidden.
run firstplan bash "$SCRIPT" "$T/plan.md" --first-success
check "firstplan: exit 0" rc_is firstplan 0
check "firstplan: ollama was never run" [ ! -e "$T/firstplan.marks/ollama-ran" ]
check "firstplan: summary lists codex only" has firstplan.out "reviewers: codex OK"
check "firstplan: note names the deliberate choice" has firstplan.out "⚠ PLAN round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --first-success was requested."

# 7. A local model outside --local-only: its review prints but does not count.
run local OLLAMA_MODEL=stub-local bash "$SCRIPT" "$T/change.diff"
check "local: its review is printed" has local.out "## Independent review — ollama (stub-local)"
check "local: no FAILED section for a policy rejection" lacks local.out "— FAILED"
check "local: summary says NOT COUNTED" has local.out "reviewers: codex OK, ollama-local NOT COUNTED (local model: sanity pass only)"
check "local: counts 1 reviewer" has local.out "landed with 1 reviewer(s) counted toward the gate"

# 8. --local-only: the one local reviewer counts (degraded), and is not called external.
run localonly OLLAMA_MODEL=stub-local bash "$SCRIPT" "$T/change.diff" --local-only
check "localonly: exit 0" rc_is localonly 0
check "localonly: codex never ran" [ ! -e "$T/localonly.marks/codex-ran" ]
check "localonly: summary" has localonly.out "reviewers: ollama-local OK"
check "localonly: note names the mode" has localonly.out "landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --local-only, degraded by owner choice."
check "localonly: not described as external" lacks localonly.out "external reviewer"

# 9. An error printed on STDOUT before a non-zero exit is quoted and classified.
run out429 CODEX_STUB=ok OLLAMA_STUB=out429 bash "$SCRIPT" "$T/change.diff"
check "out429: stdout is quoted" has out429.out "    Error: 429 Too Many Requests: weekly usage limit reached"
check "out429: classified as quota" has out429.out "reviewers: codex OK, ollama-cloud FAILED (exit 1; quota/rate limit: wait or add credits)"

# 10. A named model whose `ollama list` fails (daemon down) is a FAILED tier with its
#     error, not a silent SKIPPED; with no model named, it is skipped and stderr says why.
run listfail CODEX_STUB=ok OLLAMA_STUB=listfail OLLAMA_MODEL="$STUB_TAG" bash "$SCRIPT" "$T/change.diff"
check "listfail: FAILED section" has listfail.out "## Independent review — ollama-cloud — FAILED"
check "listfail: quotes the daemon error" has listfail.out "could not connect to ollama app"
check "listfail: summary names the preflight" has listfail.out "ollama-cloud FAILED ('ollama list' failed (is the ollama daemon running?))"
run listfailauto CODEX_STUB=ok OLLAMA_STUB=listfail bash "$SCRIPT" "$T/change.diff"
check "listfailauto: skipped, with the startup note on stderr" has listfailauto.err "'ollama list' failed — cannot auto-detect"
check "listfailauto: summary says SKIPPED" has listfailauto.out "reviewers: codex OK, ollama SKIPPED (not available)"
check "listfailauto: the note fits a skip, not a failure (round 2, ollama)" has listfailauto.out "the standard pair did not both run"
check "listfailauto: no pointer to a FAILED section that is not there" lacks listfailauto.out "each FAILED section above"

# 11. Escapes outside the simple ESC[..letter shape are stripped too.
run oddesc CODEX_STUB=ok OLLAMA_STUB=oddesc bash "$SCRIPT" "$T/change.diff"
check "oddesc: the error text survives" has oddesc.out "    Error: bad model"
check "oddesc: no escape bytes reach stdout" lacks oddesc.out $'\033'
check "oddesc: no BEL reaches stdout" lacks oddesc.out $'\007'

# 12. stderr cut mid-glyph (tail -c cuts on bytes) must not kill the quote (round 2, fresh-eyes).
run utf8cut CODEX_STUB=ok OLLAMA_STUB=utf8cut bash "$SCRIPT" "$T/change.diff"
check "utf8cut: the error is still quoted" has utf8cut.out "    Error: 429 Too Many Requests: weekly usage limit reached"
check "utf8cut: and classified as quota" has utf8cut.out "reviewers: codex OK, ollama-cloud FAILED (exit 1; quota/rate limit: wait or add credits)"

# 12b. A quota error followed by more error-shaped output than a pipe buffer holds. The
#      classifier piped those lines into grep -q, which exits at the 429; under pipefail the
#      filter it killed mid-write flipped the result to a generic failure. That is a race, lost
#      on roughly a third of runs at this size (the quote caps each file at 64 KiB, so it cannot
#      be made bigger), so each mode runs six times: as started, and with SIGPIPE ignored
#      (EPIPE instead of a signal), as on GitHub Actions runners.
bq_modes="default"
if command -v perl >/dev/null 2>&1; then bq_modes="default ignore"
else echo "SKIP bigquota with SIGPIPE ignored: it needs perl to start bash with SIGPIPE ignored"; fi
for m in $bq_modes; do
  bq_ok=1
  for k in 1 2 3 4 5 6; do
    if [ "$m" = ignore ]; then
      run bigquota CODEX_STUB=ok OLLAMA_STUB=bigquota perl -e '$SIG{PIPE}="IGNORE"; exec @ARGV' bash "$SCRIPT" "$T/change.diff"
    else run bigquota CODEX_STUB=ok OLLAMA_STUB=bigquota bash "$SCRIPT" "$T/change.diff"; fi
    has bigquota.out "reviewers: codex OK, ollama-cloud FAILED (exit 1; quota/rate limit: wait or add credits)" || bq_ok=0
  done
  check "bigquota: classified as quota on all 6 runs$([ "$m" = ignore ] && echo " (SIGPIPE ignored)")" [ "$bq_ok" = 1 ]
done

# 13. A reply rejected as not a review: its own outcome, never quota or setup advice,
#     even with an error-shaped 429 line in it (round 2, fresh-eyes; the other branch's reviewers).
run notreview CODEX_STUB=ok OLLAMA_STUB=notreview bash "$SCRIPT" "$T/change.diff"
check "notreview: exit 0 (codex counted)" rc_is notreview 0
check "notreview: FAILED section" has notreview.out "## Independent review — ollama-cloud — FAILED"
check "notreview: summary names the rejection" has notreview.out "reviewers: codex OK, ollama-cloud FAILED (output is not a review)"
check "notreview: the reply is quoted" has notreview.out "    I could not read the retry code."
check "notreview: not a quota or setup problem" has notreview.out "Not a quota or setup problem"
check "notreview: the decoy 429 is not read as quota" lacks notreview.out "quota/rate limit"
check "notreview: no sign-in advice" lacks notreview.out "sign-in"

# 14. A tracing-style codex error with trailer lines after it is still classified.
run tracing CODEX_STUB=tracing429 bash "$SCRIPT" "$T/change.diff"
check "tracing: codex classified as quota" has tracing.out "reviewers: codex FAILED (exit 1; quota/rate limit: wait or add credits), ollama-cloud OK"

# 15. A diff context line (leading space) shaped like an error is not read as quota
#     (round 2, Codex).
run codexctx CODEX_STUB=authctx bash "$SCRIPT" "$T/change.diff"
check "codexctx: an indented artifact line is not read as quota" has codexctx.out "reviewers: codex FAILED (exit 1), ollama-cloud OK"

# 16. The review-body filter consumes an escape it does not emulate (ESC[0~) instead of
#     silently ending the review there (round 2, Codex; pre-existing on main)...
run oddbody CODEX_STUB=ok OLLAMA_STUB=oddbody bash "$SCRIPT" "$T/change.diff"
check "oddbody: the finding after the escape survives" has oddbody.out "1. BUG: important finding"
check "oddbody: counted" has oddbody.out "reviewers: codex OK, ollama-cloud OK"
check "oddbody: no escape bytes" lacks oddbody.out $'\033'

# 17. ...and fails the tier on one it cannot parse, rather than counting a truncated review.
run strayesc CODEX_STUB=ok OLLAMA_STUB=strayesc bash "$SCRIPT" "$T/change.diff"
check "strayesc: FAILED, not a truncated review" has strayesc.out "reviewers: codex OK, ollama-cloud FAILED (output filter failed (exit 4))"

# 18. "disk quota exceeded" is a setup failure, not a provider refusal (round 2, ollama).
run diskquota CODEX_STUB=diskquota bash "$SCRIPT" "$T/change.diff"
check "diskquota: not read as a provider quota" has diskquota.out "reviewers: codex FAILED (exit 1), ollama-cloud OK"

# 19. A clean verdict with a qualifier between "no" and the severity word counts. On 2026-09-20
#     a genuine clean codex review reading "No confirmed BUG or RISK in the supplied diff." was
#     reported FAILED (output is not a review), and the seat was lost. Both seats share the check.
n=0
for reply in "No confirmed BUG or RISK in the supplied diff." "No definite BUG." \
             "I found no confirmed bugs in this change." "No new or confirmed RISK."; do
  n=$((n+1))
  run "verdict$n" CODEX_STUB=reply STUB_REPLY="$reply" bash "$SCRIPT" "$T/change.diff"
  check "verdict$n: codex counted — $reply" has "verdict$n.out" "reviewers: codex OK, ollama-cloud OK"
  check "verdict$n: printed as codex's review, not quoted in a FAILED section" lacks "verdict$n.out" "— FAILED"
done
run verdictollama OLLAMA_STUB=reply STUB_REPLY="No confirmed BUG or RISK in the supplied diff." bash "$SCRIPT" "$T/change.diff"
check "verdictollama: the ollama seat counts the same verdict" has verdictollama.out "reviewers: codex OK, ollama-cloud OK"
check "verdictollama: no FAILED section" lacks verdictollama.out "FAILED"

# 20. ...and what must still be rejected is: a plain refusal (a baseline: rejected before the
#     fix too), a refusal carrying the qualified verdict in a phrase the refusal check knows (it
#     runs first; the phrases it misses are pinned KNOWN WRONG in test_looks_like_review.sh), and
#     "no way to find bugs" (the qualifiers are a literal list, not any word).
n=0
for reply in "I'm sorry, but I am unable to review this diff because the repository is not available to me." \
             "No confirmed BUG or RISK, because I cannot access the diff you supplied." \
             "There is no way to find bugs in this without more context."; do
  n=$((n+1))
  run "refusal$n" CODEX_STUB=reply STUB_REPLY="$reply" bash "$SCRIPT" "$T/change.diff"
  check "refusal$n: exit 0 (ollama-cloud counted)" rc_is "refusal$n" 0
  check "refusal$n: codex rejected — $reply" has "refusal$n.out" "reviewers: codex FAILED (output is not a review), ollama-cloud OK"
done

# 21. Called from outside any git repo (a plan in a scratch dir): codex must still run,
#     in the caller's cwd, with the read-only sandbox still requested and project AGENTS.md
#     and skills kept out — on both command lines, the default and the CODEX_MODEL one.
#     Before the fix the PLAN round came back with codex FAILED and one reviewer
#     (2026-09-26). GIT_CEILING_DIRECTORIES keeps git from finding a repo above $T, wherever
#     TMPDIR lives; run() drops GIT_DIR and GIT_WORK_TREE, which a git hook exports and
#     which would otherwise override it.
mkdir -p "$T/nogit"
NOGIT="$(cd "$T/nogit" && pwd -P)"
CEILING="$(cd "$T" && pwd -P)"
for m in "" stub-override; do
  name="nogit${m:+-model}"
  run "$name" CODEX_MODEL="$m" GIT_CEILING_DIRECTORIES="$CEILING" \
    sh -c 'cd "$1" && shift && exec bash "$@"' _ "$NOGIT" "$SCRIPT" "$T/plan.md"
  check "$name: codex counted, not FAILED" has "$name.out" "reviewers: codex OK, ollama-cloud OK"
  # git=no is what git said from inside the stub itself, so the case cannot pass from
  # inside a repo (round 4, fresh-eyes).
  want="argv=[exec][-s][read-only][--skip-git-repo-check][-c][project_doc_max_bytes=0][-c][skills.include_instructions=false]${m:+[-c][model=\"$m\"]}[<prompt>] cwd=$NOGIT git=no"
  check "$name: exact argv (read-only, nothing looser), caller's cwd, outside git" \
    grep -qxF -- "$want" "$T/$name.marks/codex-args"
done

# 22. KNOWN WRONG (B-TAGCLASS), deferred with the owner's sign-off of 2026-09-26: the size arms of
# is_cloud_ollama_tag() call any "*:120b" tag cloud, even a model pulled and run locally, so it is
# refused under --local-only and counted as a cloud reviewer outside it. These pin today's wrong
# results through the real entry point, so whoever fixes the classifier changes them on purpose.
BIG_TAG="stub-big"; BIG_TAG="${BIG_TAG}:120b"   # built at runtime, like STUB_TAG
run bigtaglocal OLLAMA_MODEL="$BIG_TAG" bash "$SCRIPT" "$T/change.diff" --local-only
check "KNOWN WRONG (B-TAGCLASS): a local *:120b tag is refused under --local-only" has bigtaglocal.err "looks like a cloud tag"
check "KNOWN WRONG (B-TAGCLASS): ...with exit 2, before any reviewer runs" \
  sh -c '[ "$(cat "$1/bigtaglocal.rc")" = 2 ] && [ ! -e "$1/bigtaglocal.marks/ollama-ran" ]' _ "$T"
run bigtag OLLAMA_MODEL="$BIG_TAG" bash "$SCRIPT" "$T/change.diff"
check "KNOWN WRONG (B-TAGCLASS): a local *:120b tag counts as a cloud reviewer" has bigtag.out "reviewers: codex OK, ollama-cloud OK"
check "B-TAGCLASS guard: the tag that ran is the configured one, not the listed cloud model" \
  grep -qxF -- "$BIG_TAG" "$T/bigtag.marks/ollama-model"

# 23. Antigravity headless. With `--sandbox -p` and the MODE-line prompt, agy reached for a
#     tool needing the "command" permission, headless mode auto-denied it, and the tier exited 0
#     with no output — on 1.2.9 and again on 1.2.11 (2026-09-26). The fix asks for plan mode and
#     loosens nothing: no --dangerously-skip-permissions. The exact argv pins that on both command
#     lines, the default and the AGY_MODEL one. The stub cannot show the real CLI now answers; it
#     shows the script asks for what the manual run that did answer used.
#     The prompt: the text-only one said "You have NO tools", which is false for agy, and on
#     2026-09-27 (1.2.12, plan mode) the model tried `echo` to test it; the denial ended the run.
#     So agy gets PROMPT_AGY, which asks for no tool calls without claiming there are none, and
#     must never get the false sentence back.
for m in "" stub-agy-model; do
  name="agy${m:+-model}"
  run "$name" WITH_ANTIGRAVITY=1 AGY_MODEL="$m" bash "$SCRIPT" "$T/change.diff"
  check "$name: agy counted alongside the pair" has "$name.out" "reviewers: codex OK, ollama-cloud OK, antigravity OK"
  check "$name: header names the model" has "$name.out" "## Independent review — antigravity/agy (${m:-CLI default}"
  check "$name: header says plan mode, told not to use tools" has "$name.out" ", sandbox, plan mode, told not to use tools)"
  want="argv=[--sandbox][--mode][plan]${m:+[--model][$m]}[-p][<prompt>]"
  check "$name: exact argv (sandbox + plan mode, nothing looser)" grep -qxF -- "$want" "$T/$name.marks/agy-args"
  check "$name: sent the agy prompt" grep -qF -- "the refusal ends the run" "$T/$name.marks/agy-prompt"
  check "$name: not told the false 'You have NO tools'" not_in "$T/$name.marks/agy-prompt" "You have NO tools"
  check "$name: ollama, which really has no tools, still gets the text-only prompt" \
    grep -qF -- "You have NO tools" "$T/$name.marks/ollama-prompt"
  # 2026-10-04: the ollama seat is told that a concern about text it was not given is a
  # question. Codex can go and look, so it must not be told to hold back. agy reviews from the
  # text too, but its prompt stays as it is until its last fix is seen working (R-AGY-PROMPT).
  check "$name: the text-only prompt makes unseen text a question" \
    grep -qF -- "A BUG or RISK quotes the line of the diff that shows it" "$T/$name.marks/ollama-prompt"
  check "$name: ...and says a missing fix is named, where there is no line to quote" \
    grep -qF -- "the prior finding whose fix the diff lacks" "$T/$name.marks/ollama-prompt"
  check "$name: codex is not given that rule" \
    not_in "$T/$name.marks/codex-prompt" "A BUG or RISK quotes the line"
  check "$name: nor is agy" not_in "$T/$name.marks/agy-prompt" "A BUG or RISK quotes the line"
  check "$name: not the MODE-line prompt" not_in "$T/$name.marks/agy-prompt" "MODE: INSPECTED"
  check "$name: the artifact is in the prompt" grep -qF -- "+retry on HTTP 429 after a pause" "$T/$name.marks/agy-prompt"
  # These pin the directory agy is LAUNCHED in, not an access boundary: its tools run elsewhere
  # and can read absolute paths (see the tier table in independent_review.sh).
  check "$name: ran outside the caller's cwd" \
    sh -c '[ -s "$1" ] && [ "$(cat "$1")" != "$(pwd -P)" ]' _ "$T/$name.marks/agy-cwd"
  check "$name: in an empty dir" [ "$(cat "$T/$name.marks/agy-cwd-entries")" = 0 ]
done
# ...and if agy still comes back empty, the tier is FAILED with its stderr quoted, not dropped
# and not counted; the pair still carries the round.
run agydenied WITH_ANTIGRAVITY=1 AGY_STUB=denied bash "$SCRIPT" "$T/change.diff"
check "agydenied: exit 0 (the pair counted)" rc_is agydenied 0
check "agydenied: summary names the empty run" has agydenied.out "reviewers: codex OK, ollama-cloud OK, antigravity FAILED (exit 0 but no output)"
check "agydenied: quotes the auto-deny reason" has agydenied.out "headless mode cannot prompt for"

# 24. The default pair runs at once (2026-09-26): each reviewer sees the other start before
#     it finishes, and the sections still print in tier order, codex first. A timings line
#     follows the reviewers line. The proof is the order of events, not a clock: a 4s
#     threshold on two 2s reviewers failed under heavy load (2026-10-04, `make check` twice).
run parallel CODEX_STUB=meet OLLAMA_STUB=meet bash "$SCRIPT" "$T/change.diff"
check "parallel: both counted" has parallel.out "reviewers: codex OK, ollama-cloud OK"
check "parallel: the two reviewers' runs overlapped" \
  sh -c '[ -e "$1/codex-saw-ollama" ] && [ -e "$1/ollama-saw-codex" ]' _ "$T/parallel.marks"
check "parallel: codex's section prints before ollama's" \
  sh -c 'c=$(grep -n "^## Independent review — codex" "$1" | cut -d: -f1); o=$(grep -n "^## Independent review — ollama" "$1" | cut -d: -f1); [ -n "$c" ] && [ -n "$o" ] && [ "$c" -lt "$o" ]' _ "$T/parallel.out"
check "parallel: a timings line names both tiers" \
  grep -qE '^timings: codex [0-9]+s, ollama-cloud [0-9]+s$' "$T/parallel.out"
check "parallel: a failed tier still gets its FAILED section" has incident.out "## Independent review — ollama-cloud — FAILED"
# --first-success stays one tier at a time: the second never starts once the first counts.
run firstsucc CODEX_STUB=ok bash "$SCRIPT" "$T/change.diff" --first-success
check "first-success: ollama never ran" [ ! -e "$T/firstsucc.marks/ollama-ran" ]
check "first-success: timings name codex alone" grep -qE '^timings: codex [0-9]+s$' "$T/firstsucc.out"
# A skipped tier (not installed) has no time to report.
run notimeskip CODEX_STUB=ok OLLAMA_STUB=listfail bash "$SCRIPT" "$T/change.diff"
check "skipped tier: not in the timings line" grep -qE '^timings: codex [0-9]+s$' "$T/notimeskip.out"

# 24b. Stopping the script stops its reviewers, even one that ignores SIGTERM: none keeps
#      running (and billing) after the script is gone (round 1, fresh-eyes).
mkdir -p "$T/stop.marks"
env -u CODEX_MODEL -u CODEX_EFFORT -u OLLAMA_MODEL -u OLLAMA_HOST -u AGY_MODEL PATH="$T/bin:$PATH" HOME="$T/u" \
  WITH_ANTIGRAVITY=0 REVIEW_RAW_DIR="$T/stop.raw" STUB_MARKS="$T/stop.marks" STUB_TAG="$STUB_TAG" \
  CODEX_STUB=stubborn OLLAMA_STUB=slow bash "$SCRIPT" "$T/change.diff" >"$T/stop.out" 2>"$T/stop.err" &
spid=$!
i=0; while [ ! -s "$T/stop.marks/codex-pid" ] && [ $i -lt 50 ]; do sleep 0.1; i=$((i+1)); done
kill -TERM "$spid"; wait "$spid"; echo $? >"$T/stop.rc"
check "stop: the script exits 130" rc_is stop 130
# Gone or a zombie: once its parent subshell is killed the CLI is reparented, and a container's
# PID 1 may never reap it, so it can linger as <defunct> -- dead, not running.
check "stop: the TERM-ignoring reviewer is gone" \
  sh -c 'p=$(cat "$1"); [ -n "$p" ] && case "$(ps -o stat= -p "$p" 2>/dev/null)" in ""|Z*) true ;; *) false ;; esac' _ "$T/stop.marks/codex-pid"
# ...and a worker the CLI started itself, a grandchild of the tier's subshell (Codex, 2026-09-27).
mkdir -p "$T/stopw.marks"
env -u CODEX_MODEL -u CODEX_EFFORT -u OLLAMA_MODEL -u OLLAMA_HOST -u AGY_MODEL PATH="$T/bin:$PATH" HOME="$T/u" \
  WITH_ANTIGRAVITY=0 REVIEW_RAW_DIR="$T/stopw.raw" STUB_MARKS="$T/stopw.marks" STUB_TAG="$STUB_TAG" \
  CODEX_STUB=wrapped OLLAMA_STUB=slow bash "$SCRIPT" "$T/change.diff" >"$T/stopw.out" 2>"$T/stopw.err" &
spid=$!
i=0; while [ ! -s "$T/stopw.marks/codex-worker" ] && [ $i -lt 50 ]; do sleep 0.1; i=$((i+1)); done
kill -TERM "$spid"; wait "$spid"; echo $? >"$T/stopw.rc"
check "stop: a TERM-ignoring worker under the CLI is gone too" \
  sh -c 'p=$(cat "$1"); [ -n "$p" ] && case "$(ps -o stat= -p "$p" 2>/dev/null)" in ""|Z*) true ;; *) false ;; esac' _ "$T/stopw.marks/codex-worker"

# 25. --verify: a verification round sends the prior findings in their own block, with the
#     round's scope, to every tier; without the flag the prompt carries neither.
printf '%s\n' 'F1 BUG fixed in abc1234: retry loop never ended' 'F2 RISK waived: owner J1' >"$T/prior.md"
run verify bash "$SCRIPT" "$T/change.diff" --verify "$T/prior.md"
check "verify: exit 0" rc_is verify 0
for tier in codex ollama; do
  check "verify: $tier gets the scope paragraph" grep -qF -- "VERIFICATION ROUND." "$T/verify.marks/$tier-prompt"
  check "verify: $tier gets the prior findings, delimited" \
    sh -c 'grep -qxF -- "--- BEGIN PRIOR FINDINGS ---" "$1" && grep -qxF -- "F1 BUG fixed in abc1234: retry loop never ended" "$1" && grep -qxF -- "--- END PRIOR FINDINGS ---" "$1"' _ "$T/verify.marks/$tier-prompt"
  check "verify: $tier's prior findings come before the artifact" \
    sh -c 'p=$(grep -nxF -- "--- END PRIOR FINDINGS ---" "$1" | cut -d: -f1); a=$(grep -nxF -- "--- BEGIN diff ---" "$1" | cut -d: -f1); [ -n "$p" ] && [ -n "$a" ] && [ "$p" -lt "$a" ]' _ "$T/verify.marks/$tier-prompt"
done
run noverify bash "$SCRIPT" "$T/change.diff"
check "no --verify: no scope paragraph" not_in "$T/noverify.marks/codex-prompt" "VERIFICATION ROUND"
check "no --verify: no prior-findings block" not_in "$T/noverify.marks/ollama-prompt" "PRIOR FINDINGS"
check "no --verify: one blank line before the artifact, as before" \
  sh -c 'grep -B2 -xF -- "--- BEGIN diff ---" "$1" | head -1 | grep -qF "Every WRONG must also appear as a BUG."' _ "$T/noverify.marks/codex-prompt"
run verifynoarg bash "$SCRIPT" "$T/change.diff" --verify
check "verify without a file: exit 2" rc_is verifynoarg 2
run verifymissing bash "$SCRIPT" "$T/change.diff" --verify "$T/no-such-file.md"
check "verify with a missing file: exit 2, nothing ran" \
  sh -c '[ "$(cat "$1/verifymissing.rc")" = 2 ] && [ ! -e "$1/verifymissing.marks/codex-ran" ]' _ "$T"
printf '  \n\n' >"$T/blank.md"
run verifyblank bash "$SCRIPT" "$T/change.diff" --verify "$T/blank.md"
check "verify with an empty record: exit 2" has verifyblank.err "the prior-findings file is empty"

# 26. Codex reasoning effort (review depth, 2026-09-26): a --verify round drops to medium unless
#     CODEX_EFFORT says otherwise; "config" keeps config.toml's; an explicit value applies to any
#     round and lands after the model override, before the prompt.
base='[exec][-s][read-only][--skip-git-repo-check][-c][project_doc_max_bytes=0][-c][skills.include_instructions=false]'
argv_of() { sed -e 's/^argv=//' -e 's/ cwd=.*$//' "$T/$1.marks/codex-args"; }
run effverify bash "$SCRIPT" "$T/change.diff" --verify "$T/prior.md"
check "effort: a verify round asks for medium" \
  [ "$(argv_of effverify)" = "$base[-c][model_reasoning_effort=\"medium\"][<prompt>]" ]
check "effort: the codex header names it" has effverify.out "## Independent review — codex (stub-codex, effort medium, read-only)"
run effconfig CODEX_EFFORT=config bash "$SCRIPT" "$T/change.diff" --verify "$T/prior.md"
check "effort: CODEX_EFFORT=config keeps config.toml's, even on a verify round" \
  [ "$(argv_of effconfig)" = "$base[<prompt>]" ]
run efffull bash "$SCRIPT" "$T/change.diff"
check "effort: a full round leaves config.toml's alone" [ "$(argv_of efffull)" = "$base[<prompt>]" ]
check "effort: ...and its header says nothing about effort" has efffull.out "## Independent review — codex (stub-codex, read-only)"
run effboth CODEX_EFFORT=xhigh CODEX_MODEL=stub-strong bash "$SCRIPT" "$T/change.diff"
check "effort: explicit effort after the model override" \
  [ "$(argv_of effboth)" = "$base[-c][model=\"stub-strong\"][-c][model_reasoning_effort=\"xhigh\"][<prompt>]" ]
run effbad CODEX_EFFORT='high"' bash "$SCRIPT" "$T/change.diff"
check "effort: an unknown value exits 2 before any reviewer runs" \
  sh -c '[ "$(cat "$1/effbad.rc")" = 2 ] && [ ! -e "$1/effbad.marks/codex-ran" ]' _ "$T"

# 27. The cost log (review_log.sh, 2026-09-26): one line per attempted seat, with depth and round
#     from the flags, codex's own token count, and nothing when REVIEW_LOG=off. A log that cannot
#     be written never fails the review.
LOGT="$T/costs.tsv"
run costlog REVIEW_LOG="$LOGT" CODEX_STUB=tokens bash "$SCRIPT" "$T/change.diff" --depth normal --round 2
check "costlog: exit 0" rc_is costlog 0
check "costlog: a header and one line per seat" [ "$(wc -l <"$LOGT" | tr -d ' ')" = 3 ]
check "costlog: codex line — gate, depth, round, seat, model, effort, tokens, outcome" \
  awk -F'\t' '$8=="codex" && $5=="diff" && $6=="normal" && $7=="2" && $9=="stub-codex" && $10=="config" && $11 ~ /^[0-9]+$/ && $12=="61108" && $13=="OK" {f=1} END {exit !f}' "$LOGT"
check "costlog: ollama line" awk -F'\t' '$8=="ollama-cloud" && $10=="-" && $12=="-" && $13=="OK" {f=1} END {exit !f}' "$LOGT"
check "costlog: the timings line carries codex's tokens" grep -qE '^timings: codex [0-9]+s \(61108 tokens\), ollama-cloud [0-9]+s$' "$T/costlog.out"
run costfail REVIEW_LOG="$T/costs2.tsv" OLLAMA_STUB=429 bash "$SCRIPT" "$T/change.diff"
check "costlog: a failed seat is logged as FAILED" awk -F'\t' '$8=="ollama-cloud" && $13=="FAILED" {f=1} END {exit !f}' "$T/costs2.tsv"
run costskip REVIEW_LOG="$T/costs3.tsv" OLLAMA_STUB=listfail bash "$SCRIPT" "$T/change.diff"
check "costlog: a skipped seat is not logged" [ "$(wc -l <"$T/costs3.tsv" | tr -d ' ')" = 2 ]
DEFLOG="$T/u/.local/state/independent-review/runs.tsv"   # earlier runs here set no REVIEW_LOG
before="$(cat "$DEFLOG" 2>/dev/null | wc -l | tr -d ' ')"
run costoff REVIEW_LOG=off bash "$SCRIPT" "$T/change.diff"
check "costlog: REVIEW_LOG=off writes nothing" \
  sh -c '[ ! -e "$1/off" ] && [ ! -e "$1/u/off" ] && [ ! -e "$PWD/off" ] && [ "$(cat "$2" 2>/dev/null | wc -l | tr -d " ")" = "$3" ]' _ "$T" "$DEFLOG" "$before"
run costdefault bash "$SCRIPT" "$T/change.diff"
check "costlog: default path under the (relocated) home" [ -s "$T/u/.local/state/independent-review/runs.tsv" ]
: >"$T/notadir"
run costbad REVIEW_LOG="$T/notadir/x/costs.tsv" bash "$SCRIPT" "$T/change.diff"
check "costlog: an unwritable log never fails the review" rc_is costbad 0
check "costlog: ...and says so" has costbad.err "could not write the review cost log"
run costdepth bash "$SCRIPT" "$T/change.diff" --depth extreme
check "costlog: an unknown depth exits 2" rc_is costdepth 2
# The host logs its own seats; the summary groups by depth and seat, and counts rounds per gate.
REVIEW_LOG="$LOGT" bash "$HERE/review_log.sh" add --seat fresh-eyes --model sonnet --seconds 395 \
  --tokens 156477 --gate diff --depth normal --round 1
REVIEW_LOG="$LOGT" bash "$HERE/review_log.sh" summary >"$T/summary.out"
check "summary: a row per depth and seat" grep -qE '^normal +fresh-eyes +1 +1 +395 +395 +156477$' "$T/summary.out"
check "summary: codex row with its mean tokens" grep -qE '^normal +codex +1 +1 +[0-9]+ +[0-9]+ +61108$' "$T/summary.out"
check "summary: rounds per gate" grep -qE '^normal +1 +2\.0 +2$' "$T/summary.out"
check "summary with the log off says so, reads no file named off" \
  sh -c 'REVIEW_LOG=off bash "$1" summary | grep -qF "is off"' _ "$HERE/review_log.sh"
REVIEW_LOG="$LOGT" bash "$HERE/review_log.sh" add --model x >/dev/null 2>&1
check "add without --seat is refused" [ $? = 2 ]

# 27b. Gates (Codex, 2026-09-27): grouping by repo + branch merged two gates on a reused branch
#      into one. --round 1 now starts a gate whose id every later line carries, the host's late
#      seats included; lines from before ids existed keep the old grouping.
G="$T/gaterepo"; mkdir -p "$G"; git -C "$G" init -q
GL="$T/gates.tsv"
inrepo() { run "$1" REVIEW_LOG="$GL" sh -c 'cd "$0" && shift && exec "$@"' "$G" "${@:2}"; }
inrepo gate1a bash "$SCRIPT" "$T/change.diff" --depth normal --round 1
inrepo gate1b bash "$SCRIPT" "$T/change.diff" --depth normal --round 2
inrepo gate2a bash "$SCRIPT" "$T/change.diff" --depth normal --round 1
inrepo gate2b bash "$SCRIPT" "$T/change.diff" --depth normal --round 2
inrepo gate2c bash "$SCRIPT" "$T/change.diff" --depth normal --round 3
inrepo gatefe bash "$HERE/review_log.sh" add --seat fresh-eyes --gate diff --depth normal --round 1
# A wording pass, a final full read or a re-gate is not a round and leaves --round off (SKILL.md step 2):
# the open gate's id is what it must carry, and it must not start a gate of its own.
rows_join_gate() {   # rows_join_gate <log> <lines before> <gate id>: there are new rows, and each carries the id
  tail -n +"$(($2 + 1))" "$1" | awk -F'\t' -v g="$3" 'NF { n++; if (g == "" || $14 != g) bad = 1 } END { exit (n > 0 && !bad) ? 0 : 1 }'
}
gate_before="$(cat "$G/.git/independent-review-gate")"; lines_before="$(wc -l <"$GL")"
inrepo gatenr bash "$SCRIPT" "$T/change.diff" --depth normal
check "gates: a run with no --round is logged, under the open gate's id" rows_join_gate "$GL" "$lines_before" "$gate_before"
check "gates: a run with no --round starts no gate" [ "$(cat "$G/.git/independent-review-gate")" = "$gate_before" ]
check "gates: --round 1 leaves an id in the repo's git dir" [ -s "$G/.git/independent-review-gate" ]
check "gates: every line carries a gate id" awk -F'\t' 'NR > 1 && ($14 == "" || $14 == "-") {bad=1} END {exit bad}' "$GL"
check "gates: two ids, the late host seat in the second" \
  [ "$(awk -F'\t' 'NR > 1 {print $14}' "$GL" | sort -u | grep -c .)" = 2 ]
REVIEW_LOG="$GL" bash "$HERE/review_log.sh" summary >"$T/gates.out"
check "gates: a reused branch counts as two gates, 2 and 3 rounds" grep -qE '^normal +2 +2\.5 +3$' "$T/gates.out"
OLDL="$T/old.tsv"
printf 'date\trepo\tbranch\thead\tgate\tdepth\tround\tseat\tmodel\teffort\tseconds\ttokens\toutcome\n' >"$OLDL"
for r in 1 2 3; do printf '2026-09-20T10:00:00Z\tr\tb\th\tdiff\thigh\t%s\tcodex\tm\te\t10\t5\tOK\n' "$r" >>"$OLDL"; done
REVIEW_LOG="$OLDL" bash "$HERE/review_log.sh" summary >"$T/old.out"
check "gates: a log from before gate ids still groups by branch" grep -qE '^high +1 +3\.0 +3$' "$T/old.out"
# Many seats writing a new log at once: no line lost. This cannot force the bad interleaving
# (it never showed against the old code either); what closes it is that nothing is written
# with `>`: the header is appended like every line, so a race costs at most a spare header.
RL="$T/race.tsv"; i=0
while [ $i -lt 40 ]; do REVIEW_LOG="$RL" bash "$HERE/review_log.sh" add --seat "s$i" & i=$((i + 1)); done; wait
check "race: forty lines, none lost" [ "$(grep -vc '^date' "$RL")" = 40 ]
check "race: a header first" [ "$(awk 'NR == 1 {print $1}' "$RL")" = date ]
printf 'date\tx\n' >>"$RL"   # a spare header, as a lost race can leave: summary must skip it
REVIEW_LOG="$RL" bash "$HERE/review_log.sh" summary >"$T/race.out"
# The first table has one row per depth+seat: exactly the forty seats, nothing for the header.
check "race: a spare header is not counted as a seat" [ "$(awk 'NR > 1 && NF == 0 {exit} NR > 1' "$T/race.out" | grep -c .)" = 40 ]

# 28. The ollama HTTP API transport (2026-09-26): used when the CLI is absent (or forced). A
#     ':cloud' tag goes to ollama.com without the suffix, streamed; the key, when set, reaches
#     curl on stdin and is never in a file (#165); the tokens reach the timings line and the cost log.
NOCLI="$T/bin2:/usr/bin:/bin"
run api PATH="$NOCLI" OLLAMA_MODEL="$STUB_TAG" REVIEW_LOG="$T/api.tsv" bash "$SCRIPT" "$T/change.diff"
check "api: counted" has api.out "reviewers: codex OK, ollama-cloud OK"
check "api: header names the transport" has api.out "## Independent review — ollama ($STUB_TAG, HTTP API)"
check "api: the streamed pieces are joined" has api.out "- BUG: api finding one"
check "api: ollama.com, /api/chat" grep -qxF "https://ollama.com/api/chat" "$T/api.marks/curl-url"
check "api: the model without its :cloud suffix, streamed, carrying the artifact" \
  perl -MJSON::PP -e 'local $/; open my $f, "<", $ARGV[0] or exit 1; my $j = decode_json(<$f>); exit !($j->{model} eq "stub-model" && $j->{stream} && $j->{messages}[0]{content} =~ /--- BEGIN diff ---/)' "$T/api.marks/curl-body"
check "api: no key set, no Authorization header sent" not_in "$T/api.marks/curl-hdr" "Authorization"
check "api: tokens in the timings line" grep -qE '^timings: codex [0-9]+s, ollama-cloud [0-9]+s \(750 tokens\)$' "$T/api.out"
check "api: tokens in the cost log" awk -F'\t' '$8=="ollama-cloud" && $12=="750" && $13=="OK" {f=1} END {exit !f}' "$T/api.tsv"
run apikey PATH="$NOCLI" OLLAMA_MODEL="$STUB_TAG" OLLAMA_API_KEY=stub-secret STUB_KEY=stub-secret bash "$SCRIPT" "$T/change.diff"
check "apikey: the key reaches curl on its stdin" \
  sh -c 'grep -qxF "Authorization: Bearer stub-secret" "$1/curl-hdr" && [ -e "$1/curl-hdr-stdin" ]' _ "$T/apikey.marks"
check "apikey: and no header file is written" [ ! -e "$T/apikey.raw/ollama.hdr" ]
check "apikey: the key is nowhere on disk during the call" test ! -e "$T/apikey.marks/key-on-disk"
check "apikey: codex never sees OLLAMA_API_KEY" test ! -e "$T/apikey.marks/codex-saw-ollama-key"
run clikey CODEX_STUB=ok OLLAMA_STUB=ok OLLAMA_API_KEY=cli-secret bash "$SCRIPT" "$T/change.diff"
check "clikey: the ollama CLI still gets OLLAMA_API_KEY" grep -qxF "cli-secret" "$T/clikey.marks/ollama-cli-key"
check "clikey: codex, running beside it, does not" test ! -e "$T/clikey.marks/codex-saw-ollama-key"
check "apikey: never in any output" sh -c '! grep -rqF stub-secret "$1/apikey.out" "$1/apikey.err" "$1/apikey.raw"' _ "$T"
run api429 PATH="$NOCLI" OLLAMA_MODEL="$STUB_TAG" API_STUB=429 bash "$SCRIPT" "$T/change.diff"
check "api429: read as quota" has api429.out "ollama-cloud FAILED (HTTP 429; quota/rate limit: wait or add credits)"
check "api429: the API's message is quoted" has api429.out "weekly usage limit"
run apitrunc PATH="$NOCLI" OLLAMA_MODEL="$STUB_TAG" API_STUB=trunc bash "$SCRIPT" "$T/change.diff"
check "apitrunc: a stream without its done line fails the tier, named as truncated" has apitrunc.out "ollama-cloud FAILED (truncated review (HTTP 200))"
check "apitrunc: and says it was truncated" has apitrunc.out "a truncated review"
run apitrunc429 PATH="$NOCLI" OLLAMA_MODEL="$STUB_TAG" API_STUB=trunc429 bash "$SCRIPT" "$T/change.diff"
check "apitrunc429: a 429-chunk truncated stream is not read as quota" \
  sh -c 'grep -qF "ollama-cloud FAILED (truncated review (HTTP 200))" "$1" && ! grep -qF "quota/rate limit: wait" "$1"' _ "$T/apitrunc429.out"
run apinonjson PATH="$NOCLI" OLLAMA_MODEL="$STUB_TAG" API_STUB=nonjson200 bash "$SCRIPT" "$T/change.diff"
check "apinonjson: review text on a non-JSON 200 line is quoted below, not read as quota" \
  sh -c 'grep -qF "ollama-cloud FAILED (a stream line that is not JSON (HTTP 200))" "$1" && ! grep -qF "quota/rate limit: wait" "$1" && grep -qF "line began:" "$1"' _ "$T/apinonjson.out"
run apimiderr PATH="$NOCLI" OLLAMA_MODEL="$STUB_TAG" API_STUB=miderr200 bash "$SCRIPT" "$T/change.diff"
check "apimiderr: an error line in a 200 stream is named as an error mid-stream" \
  sh -c 'grep -qF "ollama-cloud FAILED (error mid-stream (HTTP 200))" "$1" && grep -qF "upstream overloaded" "$1"' _ "$T/apimiderr.out"
run apiempty PATH="$NOCLI" OLLAMA_MODEL="$STUB_TAG" API_STUB=empty200 bash "$SCRIPT" "$T/change.diff"
check "apiempty: an empty 200 reply is named as empty, not truncated" \
  sh -c 'grep -qF "ollama-cloud FAILED (empty reply (HTTP 200))" "$1" && ! grep -qF "truncated" "$1"' _ "$T/apiempty.out"
run apihtml PATH="$NOCLI" OLLAMA_MODEL="$STUB_TAG" API_STUB=html200 bash "$SCRIPT" "$T/change.diff"
check "apihtml: a 200 page whose first line is not JSON is named as not a stream, as Melious names it" \
  sh -c 'grep -qF "ollama-cloud FAILED (not a stream (HTTP 200))" "$1" && grep -qF "line began: <html>" "$1"' _ "$T/apihtml.out"
run api502 PATH="$NOCLI" OLLAMA_MODEL="$STUB_TAG" API_STUB=502 bash "$SCRIPT" "$T/change.diff"
check "api502: a non-JSON error body is quoted" has api502.out "response is not JSON: upstream request failed"
check "api502: ...and the summary keeps the status" has api502.out "ollama-cloud FAILED (HTTP 502)"
run apidown PATH="$NOCLI" OLLAMA_MODEL="$STUB_TAG" API_STUB=down bash "$SCRIPT" "$T/change.diff"
check "apidown: a network failure names curl's exit" has apidown.out "ollama-cloud FAILED (curl exit 56)"
check "apidown: ...with a hint" has apidown.out "is the host allowed by the network policy?"
run apinomodel PATH="$NOCLI" bash "$SCRIPT" "$T/change.diff"
check "apinomodel: no CLI and no model — skipped" has apinomodel.out "ollama SKIPPED (not available)"
check "apinomodel: the note names OLLAMA_MODEL" has apinomodel.err "Set OLLAMA_MODEL=<name>:cloud"
check "apinomodel: nothing was sent" [ ! -e "$T/apinomodel.marks/curl-url" ]
run apiforced OLLAMA_TRANSPORT=api OLLAMA_MODEL="$STUB_TAG" bash "$SCRIPT" "$T/change.diff"
check "apiforced: OLLAMA_TRANSPORT=api wins over an installed CLI" \
  sh -c '[ -e "$1/curl-url" ] && [ ! -e "$1/ollama-ran" ]' _ "$T/apiforced.marks"
run apibadtransport OLLAMA_TRANSPORT=grpc bash "$SCRIPT" "$T/change.diff"
check "an unknown OLLAMA_TRANSPORT exits 2" rc_is apibadtransport 2
run apilocal PATH="$NOCLI" OLLAMA_MODEL=stub-local OLLAMA_HOST=127.0.0.1:11434 bash "$SCRIPT" "$T/change.diff"
check "apilocal: a local tag goes to OLLAMA_HOST" grep -qxF "http://127.0.0.1:11434/api/chat" "$T/apilocal.marks/curl-url"
check "apilocal: with its tag unchanged" grep -qF '"model":"stub-local"' "$T/apilocal.marks/curl-body"
check "apilocal: and stays a sanity pass" has apilocal.out "ollama-local NOT COUNTED (local model: sanity pass only)"

# 29. --seat runs ONE named reviewer (2026-09-26: the wording pass and the final full read).
run seatollama bash "$SCRIPT" "$T/change.diff" --seat ollama
check "seat ollama: a successful single-seat run exits 0" rc_is seatollama 0
check "seat ollama: only ollama ran" sh -c '[ -e "$1/ollama-ran" ] && [ ! -e "$1/codex-ran" ]' _ "$T/seatollama.marks"
check "seat ollama: the summary names it alone" has seatollama.out "reviewers: ollama-cloud OK"
check "seat ollama: the one-reviewer note says it was asked for" has seatollama.out "--seat ollama was requested"
check "seat ollama: ...and when one reviewer is right" has seatollama.out "any other round needs the standard pair"
# A run without --depth says so, on stdout and stderr; a run with it does not (2026-10-04: 27 of
# 51 trails in one repo named no depth).
check "depth: a run without --depth is told to state one" has seatollama.out "depth: not stated"
check "depth: ...on stderr too" has seatollama.err "depth: not stated"
check "depth: a run with --depth is not, on either stream" \
  sh -c '! grep -qF "depth: not stated" "$1/costlog.out" "$1/costlog.err"' _ "$T"
run seatfirst bash "$SCRIPT" "$T/change.diff" --seat codex --first-success
check "seat: with --first-success exits 2" rc_is seatfirst 2
run seatwithagy WITH_ANTIGRAVITY=1 bash "$SCRIPT" "$T/change.diff" --seat ollama
check "seat: another seat with the Antigravity opt-in exits 2" rc_is seatwithagy 2
run seatagyboth bash "$SCRIPT" "$T/change.diff" --seat agy --with-antigravity
check "seat agy with --with-antigravity is allowed (same reviewer)" has seatagyboth.out "reviewers: antigravity OK"
check "seat agy with --with-antigravity: exactly one Antigravity section, no other seat" \
  sh -c '[ "$(grep -c "^## Independent review — antigravity" "$1/seatagyboth.out")" = 1 ] && [ ! -e "$1/seatagyboth.marks/codex-ran" ] && [ ! -e "$1/seatagyboth.marks/ollama-ran" ]' _ "$T"
run seatcodex bash "$SCRIPT" "$T/change.diff" --seat codex
check "seat codex: only codex ran" sh -c '[ -e "$1/codex-ran" ] && [ ! -e "$1/ollama-ran" ]' _ "$T/seatcodex.marks"
run seatagy bash "$SCRIPT" "$T/change.diff" --seat agy
check "seat agy: names Antigravity, so it runs without WITH_ANTIGRAVITY" has seatagy.out "reviewers: antigravity OK"
run seatbad bash "$SCRIPT" "$T/change.diff" --seat gemini
check "seat: an unknown seat exits 2" rc_is seatbad 2
run seatlocal OLLAMA_MODEL=stub-local bash "$SCRIPT" "$T/change.diff" --local-only --seat codex
check "seat: --local-only refuses an external seat, exit 2, nothing ran" \
  sh -c '[ "$(cat "$1/seatlocal.rc")" = 2 ] && [ ! -e "$1/seatlocal.marks/codex-ran" ]' _ "$T"

# 30. merge_link.sh (2026-09-26): the merge link's artifact, on real merges. Both reviewers of
#     the change that introduced it found a way the one-line command lost a file: a path with a
#     space (round 1) and an own edit the merge threw away (the final full read).
ML="$HERE/merge_link.sh"
if command -v git >/dev/null 2>&1; then
  R="$T/mlrepo"; mkdir -p "$R"
  (
    cd "$R" && git init -q -b main && git config user.email t@t && git config user.name t
    mkdir -p "dir with space" "lib dir" docs/reviews
    echo base >"dir with space/f.txt"; echo base >own.txt; echo base >'[g]*.txt'; echo base >keep.txt
    echo base >callee.txt; echo base >g1.txt; echo base >docs/reviews/trail.md
    echo base >other.txt; echo base >"lib dir/space callee.sh"
    git add -A && git commit -qm base && git tag oldbase
    git checkout -qb feat
    echo feature >>"dir with space/f.txt"; echo "my change" >own.txt; echo feature >>'[g]*.txt'
    printf 'feature\nimport callee\nrun space callee.sh\nsee own notes\n' >>keep.txt; echo round >>docs/reviews/trail.md
    git commit -qam feat && git tag reviewed
    git checkout -q main
    echo main >"dir with space/f.txt"; echo "main change" >own.txt; echo main >callee.txt; echo "main other" >g1.txt
    echo main >other.txt; echo main >"lib dir/space callee.sh"
    git commit -qam main
    git checkout -q feat
    git merge -q main >/dev/null 2>&1 || true
    printf 'resolved\n' >"dir with space/f.txt"        # a merge effect on a spaced path
    git checkout --theirs own.txt                      # the merge throws the own edit away
    git add -A && git commit -qm merge && git tag newhead
    git tag newbase "$(git merge-base main HEAD)"
  ) >/dev/null 2>&1
  ( cd "$R" && bash "$ML" oldbase reviewed newbase ) >"$T/ml.out" 2>"$T/ml.err"; echo $? >"$T/ml.rc"
  check "merge_link: exit 0" rc_is ml 0
  check "merge_link: the spaced path's merge effect is in" has ml.out "+resolved"
  check "merge_link: the own edit the merge threw away is in" has ml.out "-my change"
  check "merge_link: a glob-character name is taken literally, matching no other file" lacks ml.out "b/g1.txt"
  check "merge_link: an unmoved own file is not" lacks ml.out "b/keep.txt"
  check "merge_link: the review trail is left out" lacks ml.out "docs/reviews/trail.md"
  check "merge_link: a base-only file is not in, unless named" lacks ml.out "b/callee.txt"
  ( cd "$R" && bash "$ML" oldbase reviewed newbase -- callee.txt ) >"$T/mlx.out" 2>&1
  check "merge_link: an extra path the change calls is added" has mlx.out "+main"
  check "merge_link: no suggestions unless asked" not_in "$T/ml.err" "base side"
  # --suggest-callees (F5 of the trail that introduced the merge link): base-side files the merge
  # changed that the change's own files name are listed on stderr, never added to the diff.
  ( cd "$R" && bash "$ML" --suggest-callees oldbase reviewed newbase ) >"$T/mls.out" 2>"$T/mls.err"; echo $? >"$T/mls.rc"
  check "suggest: exit 0" rc_is mls 0
  check "suggest: the diff on stdout is unchanged" cmp -s "$T/ml.out" "$T/mls.out"
  check "suggest: a file named by its module name alone is suggested" grep -qxF "  callee.txt" "$T/mls.err"
  check "suggest: a spaced path is suggested whole" grep -qxF "  lib dir/space callee.sh" "$T/mls.err"
  check "suggest: a base-side file no own file names is not" not_in "$T/mls.err" "g1.txt"
  check "suggest: an own file is not suggested (already in the diff)" not_in "$T/mls.err" "  own.txt"
  check "suggest: only own files are searched, named literally ('[g]*.txt' is not g1.txt)" \
    not_in "$T/mls.err" "other.txt"
  ( cd "$R" && bash "$ML" --suggest-callees oldbase reviewed newbase -- callee.txt ) >/dev/null 2>"$T/mlsx.err"
  check "suggest: a path already passed after -- is not suggested again" not_in "$T/mlsx.err" "  callee.txt"
  ( cd "$R" && bash "$ML" --suggest-callees reviewed reviewed oldbase ) >/dev/null 2>"$T/mlsnone.err"; echo $? >"$T/mlsnone.rc"
  check "suggest: none found says so, exit 0" \
    sh -c '[ "$(cat "$1/mlsnone.rc")" = 0 ] && grep -qF "no file the merge changed on the base side" "$1/mlsnone.err"' _ "$T"
  ( cd "$R" && bash "$ML" oldbase reviewed newbase --suggest-callees ) >/dev/null 2>&1; echo $? >"$T/mlslate.rc"
  check "suggest: the flag goes first, elsewhere it is a usage error" rc_is mlslate 2
  ( cd "$R" && bash "$ML" --suggest-callees newhead newhead newhead ) >"$T/mlsown.out" 2>"$T/mlsown.err"
  check "suggest: no own files to search says so, not silence (Light gate, #193)" \
    sh -c '[ ! -s "$1/mlsown.out" ] && grep -qF "no files of its own" "$1/mlsown.err"' _ "$T"
  ( cd "$R" && bash "$ML" newhead newhead newhead ) >"$T/mlempty.out" 2>&1; echo $? >"$T/mlempty.rc"
  check "merge_link: nothing moved prints nothing (not the whole tree)" \
    sh -c '[ "$(cat "$1/mlempty.rc")" = 0 ] && [ ! -s "$1/mlempty.out" ]' _ "$T"
  ( cd "$R" && bash "$ML" oldbase no-such-rev newbase ) >/dev/null 2>&1; echo $? >"$T/mlbad.rc"
  check "merge_link: an unknown revision exits 2" rc_is mlbad 2
  # A rename is listed by its new name alone, so a merge that brings the old name back lost it
  # (round 4, Codex): with both names kept the merge link printed nothing at all.
  for mode in drop keep; do
    R="$T/mlrename-$mode"; mkdir -p "$R"
    (
      cd "$R" && git init -q -b main && git config user.email t@t && git config user.name t
      printf 'one\ntwo\nthree\nfour\nfive\nsix\n' >old.txt; echo base >other.txt
      git add -A && git commit -qm base && git tag oldbase
      git checkout -qb feat && git mv old.txt new.txt && echo "my edit" >>new.txt
      git commit -qam rename && git tag reviewed
      git checkout -q main && echo main >>other.txt && git commit -qam main
      git checkout -q feat && git merge -q --no-commit --no-ff main
      if [ "$mode" = drop ]; then git rm -qf new.txt; fi
      git checkout main -- old.txt                     # the merge brings the old name back
      git add -A && git commit -qm merge && git tag newbase "$(git merge-base main HEAD)"
    ) >/dev/null 2>&1
    ( cd "$R" && bash "$ML" oldbase reviewed newbase ) >"$T/mlrn-$mode.out" 2>&1
    check "merge_link: a rename the merge undid ($mode the new name) shows the old name" has "mlrn-$mode.out" "old.txt"
  done
fi

# 31. A reasoning model's trace is kept out of the answer (2026-09-27): its trace quoted the
#     prompt's "could not read" advice, and the whole reply was rejected as not a review.
run think OLLAMA_STUB=think bash "$SCRIPT" "$T/change.diff"
check "think: the CLI is asked to hide the trace" test -e "$T/think.marks/ollama-hidethinking"
check "think: ollama-cloud counted, not FAILED" has think.out "reviewers: codex OK, ollama-cloud OK"
check "think: the answer is printed, the trace is not" \
  sh -c 'grep -qF "RISK — retry.rb:12" "$1" && ! grep -qF "Thinking..." "$1"' _ "$T/think.out"
check "think: the model and prompt still reach the CLI" \
  sh -c 'grep -qxF "$2" "$1/ollama-model" && [ -s "$1/ollama-prompt" ]' _ "$T/think.marks" "$STUB_TAG"
run thinkold STUB_OLDCLI=1 OLLAMA_STUB=think bash "$SCRIPT" "$T/change.diff"
check "thinkold: a CLI without the flag is not given it" test ! -e "$T/thinkold.marks/ollama-hidethinking"
check "thinkold: ...and still runs the model, as before this change" test -e "$T/thinkold.marks/ollama-ran"
for how in failhelp longword; do   # round 1, Codex: a failed help, or the flag inside a longer word
  run "think$how" STUB_OLDCLI=$how OLLAMA_STUB=think bash "$SCRIPT" "$T/change.diff"
  check "think$how: the flag is not passed" test ! -e "$T/think$how.marks/ollama-hidethinking"
done

# 32. The Melious fallback for the ollama seat (2026-10-05): it runs only when MELIOUS_MODEL names
#     a model and the ollama seat did not count, or as --seat melious. Same text-only prompt.
run mfall OLLAMA_STUB=429 MELIOUS_MODEL=stub-melious REVIEW_LOG="$T/mfall.tsv" bash "$SCRIPT" "$T/change.diff"
check "mfall: ollama refused, melious stands in and counts" \
  has mfall.out "reviewers: codex OK, ollama-cloud FAILED (exit 1; quota/rate limit: wait or add credits), melious OK"
check "mfall: two counted, so no fewer-than-2 note" lacks mfall.out "fewer than the 2"
check "mfall: its section header" has mfall.out "## Independent review — melious (stub-melious, HTTP API)"
check "mfall: the streamed pieces are joined" has mfall.out "- BUG: melious finding one"
check "mfall: the reasoning trace is not the answer" lacks mfall.out "Thinking: I could not read"
check "mfall: Melious's chat completions endpoint" grep -qxF "https://api.melious.ai/v1/chat/completions" "$T/mfall.marks/melious-url"
check "mfall: the model, streamed, the text-only prompt" \
  perl -MJSON::PP -e 'local $/; open my $f, "<", $ARGV[0] or exit 1; my $j = decode_json(<$f>); exit !($j->{model} eq "stub-melious" && $j->{stream} && $j->{messages}[0]{content} =~ /You have NO tools/ && $j->{messages}[0]{content} =~ /--- BEGIN diff ---/)' "$T/mfall.marks/melious-body"
check "mfall: no key set, no Authorization header sent" not_in "$T/mfall.marks/melious-hdr" "Authorization"
check "mfall: tokens in the timings line" grep -qE '^timings: codex [0-9]+s, ollama-cloud [0-9]+s, melious [0-9]+s \(600 tokens\)$' "$T/mfall.out"
check "mfall: tokens in the cost log" awk -F'\t' '$8=="melious" && $9=="stub-melious" && $12=="600" && $13=="OK" {f=1} END {exit !f}' "$T/mfall.tsv"
run mnomodel OLLAMA_STUB=429 bash "$SCRIPT" "$T/change.diff"
check "mnomodel: no MELIOUS_MODEL, no Melious seat and no call" \
  sh -c '! grep -qF melious "$1/mnomodel.out" && [ ! -e "$1/mnomodel.marks/melious-url" ]' _ "$T"
run mpair MELIOUS_MODEL=stub-melious bash "$SCRIPT" "$T/change.diff"
check "mpair: ollama counted, so Melious is not called" \
  sh -c 'grep -qF "reviewers: codex OK, ollama-cloud OK" "$1/mpair.out" && ! grep -qF melious "$1/mpair.out" && [ ! -e "$1/mpair.marks/melious-url" ]' _ "$T"
run mnocli PATH="$NOCLI" MELIOUS_MODEL=stub-melious bash "$SCRIPT" "$T/change.diff"
check "mnocli: no ollama at all, Melious runs with the pair" has mnocli.out "reviewers: codex OK, ollama SKIPPED (not available), melious OK"
check "mnocli: the no-CLI note names MELIOUS_MODEL" has mnocli.err "MELIOUS_MODEL=<model> sends the seat to Melious instead"
run mlocal OLLAMA_MODEL=stub-local MELIOUS_MODEL=stub-melious bash "$SCRIPT" "$T/change.diff"
check "mlocal: a local sanity pass does not count, so Melious runs" \
  has mlocal.out "reviewers: codex OK, ollama-local NOT COUNTED (local model: sanity pass only), melious OK"
run mkey OLLAMA_STUB=429 MELIOUS_MODEL=stub-melious MELIOUS_API_KEY=stub-msecret bash "$SCRIPT" "$T/change.diff"
check "mkey: the key reaches curl on its stdin" \
  sh -c 'grep -qxF "Authorization: Bearer stub-msecret" "$1/melious-hdr" && [ -e "$1/melious-hdr-stdin" ]' _ "$T/mkey.marks"
check "mkey: and no header file is written" [ ! -e "$T/mkey.raw/melious.hdr" ]
check "mkey: never in any output" sh -c '! grep -rqF stub-msecret "$1/mkey.out" "$1/mkey.err" "$1/mkey.raw"' _ "$T"
run m429 OLLAMA_STUB=429 MELIOUS_MODEL=stub-melious MELIOUS_STUB=429 bash "$SCRIPT" "$T/change.diff"
check "m429: read as quota" has m429.out "melious FAILED (HTTP 429; quota/rate limit: wait or add credits)"
check "m429: the API's message is quoted" has m429.out "Rate limit exceeded for your plan"
check "m429: the FAILED section names the model" has m429.out "Model: stub-melious"
run mtrunc OLLAMA_STUB=429 MELIOUS_MODEL=stub-melious MELIOUS_STUB=trunc bash "$SCRIPT" "$T/change.diff"
check "mtrunc: a stream with no finish_reason or [DONE] fails the tier, named as truncated" \
  sh -c 'grep -qF "melious FAILED (truncated review (HTTP 200))" "$1" && grep -qF "a truncated review" "$1"' _ "$T/mtrunc.out"
run mlength OLLAMA_STUB=429 MELIOUS_MODEL=stub-melious MELIOUS_STUB=length bash "$SCRIPT" "$T/change.diff"
check "mlength: finish_reason length fails the tier" \
  sh -c 'grep -qF "melious FAILED (truncated review (HTTP 200))" "$1" && grep -qF "finish_reason length" "$1"' _ "$T/mlength.out"
run mthink OLLAMA_STUB=429 MELIOUS_MODEL=stub-melious MELIOUS_STUB=inlinethink bash "$SCRIPT" "$T/change.diff"
check "mthink: an inline think block is cut, and the review counts" \
  sh -c 'grep -qF "melious OK" "$1" && grep -qF -- "- RISK: inline finding" "$1" && ! grep -qF "could not read the file" "$1"' _ "$T/mthink.out"
run mmiderr OLLAMA_STUB=429 MELIOUS_MODEL=stub-melious MELIOUS_STUB=miderr bash "$SCRIPT" "$T/change.diff"
check "mmiderr: an error object mid-stream fails the tier and is quoted" \
  sh -c 'grep -qF "melious FAILED (error mid-stream (HTTP 200))" "$1" && grep -qF "upstream overloaded" "$1"' _ "$T/mmiderr.out"
run mnotstream OLLAMA_STUB=429 MELIOUS_MODEL=stub-melious MELIOUS_STUB=notstream bash "$SCRIPT" "$T/change.diff"
check "mnotstream: a plain JSON reply past 4 KB is named as not a stream, and quoted" \
  sh -c 'grep -qF "not a stream (stream:true ignored?)" "$1" && grep -qF "finding number 0" "$1" && ! grep -qF "truncated" "$1"' _ "$T/mnotstream.out"
check "mnotstream: a 429 inside the quoted review is not read as quota (round 3, fresh-eyes)" \
  sh -c 'grep -qF "melious FAILED (not a stream (HTTP 200))" "$1" && ! grep -qE "melious FAILED \([^;]*; quota" "$1"' _ "$T/mnotstream.out"
run msplit OLLAMA_STUB=429 MELIOUS_MODEL=stub-melious MELIOUS_STUB=splitchunk bash "$SCRIPT" "$T/change.diff"
check "msplit: review text in a non-JSON chunk is quoted, not read as quota (re-gate, fresh-eyes)" \
  sh -c 'grep -qF "melious FAILED (a stream chunk that is not JSON (HTTP 200))" "$1" && ! grep -qE "melious FAILED \([^;]*; quota" "$1" && grep -qF "chunk began:" "$1"' _ "$T/msplit.out"
run mcr OLLAMA_STUB=429 MELIOUS_MODEL=stub-melious MELIOUS_STUB=crchunk bash "$SCRIPT" "$T/change.diff"
check "mcr: a control byte in a quoted chunk cannot start an error line (second re-gate, fresh-eyes)" \
  sh -c 'grep -qF "melious FAILED (a stream chunk that is not JSON (HTTP 200))" "$1" && ! grep -qE "melious FAILED \([^;]*; quota" "$1"' _ "$T/mcr.out"
run mbad502 OLLAMA_STUB=429 MELIOUS_MODEL=stub-melious MELIOUS_STUB=bad502 bash "$SCRIPT" "$T/change.diff"
check "mbad502: a non-JSON 502 body is quoted on one line, control bytes collapsed" \
  sh -c 'grep -qF "response is not JSON: upstream Error: bad gateway [1Gfailed" "$1" && grep -qF "melious FAILED (HTTP 502)" "$1"' _ "$T/mbad502.out"
run mnotstreamerr OLLAMA_STUB=429 MELIOUS_MODEL=stub-melious MELIOUS_STUB=notstreamerr bash "$SCRIPT" "$T/change.diff"
check "mnotstreamerr: a 200 reply carrying an error message is classified by that message" \
  has mnotstreamerr.out "melious FAILED (error reply, not a stream (HTTP 200); quota/rate limit: wait or add credits)"
run mhtml OLLAMA_STUB=429 MELIOUS_MODEL=stub-melious MELIOUS_STUB=html bash "$SCRIPT" "$T/change.diff"
check "mhtml: a 200 page that is neither a stream nor JSON is named and quoted, not read as truncated" \
  sh -c 'grep -qF "melious FAILED (not a stream (HTTP 200))" "$1" && grep -qF "reply began: <html>" "$1" && ! grep -qF "truncated" "$1"' _ "$T/mhtml.out"
run mkeepalive OLLAMA_STUB=429 MELIOUS_MODEL=stub-melious MELIOUS_STUB=keepalive bash "$SCRIPT" "$T/change.diff"
check "mkeepalive: keep-alive comments, then a closed stream: a truncated review, not \"not a stream\"" \
  sh -c 'grep -qF "melious FAILED (truncated review (HTTP 200))" "$1" && ! grep -qF "not a stream" "$1"' _ "$T/mkeepalive.out"
run mempty OLLAMA_STUB=429 MELIOUS_MODEL=stub-melious MELIOUS_STUB=empty bash "$SCRIPT" "$T/change.diff"
check "mempty: an empty 200 reply is named as empty, not truncated" \
  sh -c 'grep -qF "an empty reply" "$1" && grep -qF "melious FAILED (empty reply (HTTP 200))" "$1" && ! grep -qF "truncated" "$1"' _ "$T/mempty.out"
run mdown OLLAMA_STUB=429 MELIOUS_MODEL=stub-melious MELIOUS_STUB=down bash "$SCRIPT" "$T/change.diff"
check "mdown: a network failure names curl's exit, with a hint" \
  sh -c 'grep -qF "melious FAILED (curl exit 56)" "$1" && grep -qF "is the host allowed by the network policy?" "$1"' _ "$T/mdown.out"
# The fallback waits for ollama alone, not for codex (round 1, fresh-eyes). A handshake, not wall
# time (rounds 2 and 3): codex finishes only once Melious has started, so code that holds Melious
# back until codex is done shows as melious-after-codex after codex's 10s cap.
run mparallel CODEX_STUB=waitmelious OLLAMA_STUB=429 MELIOUS_MODEL=stub-melious MELIOUS_STUB=slow bash "$SCRIPT" "$T/change.diff"
check "mparallel: melious counted" has mparallel.out "melious OK"
check "mparallel: Melious started while codex was still running" \
  sh -c '[ -e "$1/codex-done" ] && [ ! -e "$1/melious-after-codex" ]' _ "$T/mparallel.marks"
# Stopping the script stops a fallback started after ollama failed, as it does the pair.
mkdir -p "$T/mstop.marks"
env -u CODEX_MODEL -u CODEX_EFFORT -u REVIEW_LOG -u XDG_STATE_HOME -u OLLAMA_API_KEY -u OLLAMA_TRANSPORT -u OLLAMA_MODEL -u OLLAMA_HOST -u AGY_MODEL -u MELIOUS_API_KEY -u MELIOUS_MAX_TOKENS -u MELIOUS_BASE_URL -u MELIOUS_ENV_FILE -u MELIOUS_API_TIMEOUT -u SECOND_SEAT -u GIT_DIR -u GIT_WORK_TREE \
  PATH="$T/bin:$PATH" HOME="$T/u" WITH_ANTIGRAVITY=0 REVIEW_RAW_DIR="$T/mstop.raw" STUB_MARKS="$T/mstop.marks" STUB_TAG="$STUB_TAG" \
  CODEX_STUB=slow OLLAMA_STUB=429 MELIOUS_MODEL=stub-melious MELIOUS_STUB=stubborn MELIOUS_API_KEY=stub-stopkey \
  bash "$SCRIPT" "$T/change.diff" >"$T/mstop.out" 2>"$T/mstop.err" &
spid=$!
i=0; while [ ! -s "$T/mstop.marks/melious-pid" ] && [ $i -lt 50 ]; do sleep 0.1; i=$((i+1)); done
kill -TERM "$spid"; wait "$spid"; echo $? >"$T/mstop.rc"
check "mstop: the script exits 130" rc_is mstop 130
check "mstop: the key reached curl, and no copy of it is left in RAW_DIR (final full read, deepseek)" \
  sh -c 'grep -qxF "Authorization: Bearer stub-stopkey" "$1/mstop.marks/melious-hdr" && ! grep -rqF stub-stopkey "$1/mstop.raw"' _ "$T"
check "mstop: the TERM-ignoring fallback is gone" \
  sh -c 'p=$(cat "$1"); [ -n "$p" ] && case "$(ps -o stat= -p "$p" 2>/dev/null)" in ""|Z*) true ;; *) false ;; esac' _ "$T/mstop.marks/melious-pid"
run mseat MELIOUS_MODEL=stub-melious bash "$SCRIPT" "$T/change.diff" --seat melious
check "mseat: only Melious ran" \
  sh -c 'grep -qF "reviewers: melious OK" "$1/mseat.out" && [ ! -e "$1/mseat.marks/codex-ran" ] && [ ! -e "$1/mseat.marks/ollama-ran" ]' _ "$T"
run mseatnomodel bash "$SCRIPT" "$T/change.diff" --seat melious
check "mseatnomodel: --seat melious without a model is skipped, exit 4" \
  sh -c 'grep -qF "reviewers: melious SKIPPED (not available)" "$1/mseatnomodel.out" && [ "$(cat "$1/mseatnomodel.rc")" = 4 ]' _ "$T"
run mfirst CODEX_STUB=auth OLLAMA_STUB=429 MELIOUS_MODEL=stub-melious bash "$SCRIPT" "$T/change.diff" --first-success
check "mfirst: --first-success falls through to Melious after ollama" \
  has mfirst.out "reviewers: codex FAILED (exit 1), ollama-cloud FAILED (exit 1; quota/rate limit: wait or add credits), melious OK"
run mlocalonly OLLAMA_MODEL=stub-local MELIOUS_MODEL=stub-melious bash "$SCRIPT" "$T/change.diff" --local-only
check "mlocalonly: --local-only never calls Melious" \
  sh -c '! grep -qF melious "$1/mlocalonly.out" && [ ! -e "$1/mlocalonly.marks/melious-url" ]' _ "$T"
run mlocalseat OLLAMA_MODEL=stub-local MELIOUS_MODEL=stub-melious bash "$SCRIPT" "$T/change.diff" --local-only --seat melious
check "mlocalseat: --local-only refuses --seat melious, exit 2" \
  sh -c '[ "$(cat "$1/mlocalseat.rc")" = 2 ] && [ ! -e "$1/mlocalseat.marks/melious-url" ]' _ "$T"

# 32b. SECOND_SEAT=melious (2026-10-06): Melious holds the second seat and ollama is its fallback,
#      the other way round from section 32. A refused Melious seat must still hand over, or the
#      round lands with one reviewer.
run sfirst SECOND_SEAT=melious MELIOUS_MODEL=stub-melious bash "$SCRIPT" "$T/change.diff"
check "sfirst: Melious runs with Codex and counts" has sfirst.out "reviewers: codex OK, melious OK"
check "sfirst: ollama is not run while Melious counts" [ ! -e "$T/sfirst.marks/ollama-ran" ]
check "sfirst: two counted, so no fewer-than-2 note" lacks sfirst.out "fewer than the 2"
run sfall SECOND_SEAT=melious MELIOUS_MODEL=stub-melious MELIOUS_STUB=429 bash "$SCRIPT" "$T/change.diff"
check "sfall: Melious out of credits, ollama stands in and counts" \
  has sfall.out "reviewers: codex OK, melious FAILED (HTTP 429; quota/rate limit: wait or add credits), ollama-cloud OK"
check "sfall: ollama ran" [ -e "$T/sfall.marks/ollama-ran" ]
run sparallel CODEX_STUB=waitmelious SECOND_SEAT=melious MELIOUS_MODEL=stub-melious MELIOUS_STUB=slow bash "$SCRIPT" "$T/change.diff"
check "sparallel: Melious started while codex was still running" \
  sh -c 'grep -qF "melious OK" "$1/sparallel.out" && [ -e "$1/sparallel.marks/codex-done" ] && [ ! -e "$1/sparallel.marks/melious-after-codex" ]' _ "$T"
run sfirstsucc CODEX_STUB=auth SECOND_SEAT=melious MELIOUS_MODEL=stub-melious MELIOUS_STUB=429 bash "$SCRIPT" "$T/change.diff" --first-success
check "sfirstsucc: --first-success tries Melious before ollama" \
  has sfirstsucc.out "reviewers: codex FAILED (exit 1), melious FAILED (HTTP 429; quota/rate limit: wait or add credits), ollama-cloud OK"
run snomodel SECOND_SEAT=melious bash "$SCRIPT" "$T/change.diff"
check "snomodel: SECOND_SEAT=melious without a model stops before any call, exit 2" \
  sh -c '[ "$(cat "$1/snomodel.rc")" = 2 ] && grep -qF "needs MELIOUS_MODEL" "$1/snomodel.err" && [ ! -e "$1/snomodel.marks/codex-ran" ]' _ "$T"
run sbad SECOND_SEAT=gpt MELIOUS_MODEL=stub-melious bash "$SCRIPT" "$T/change.diff"
check "sbad: an unknown SECOND_SEAT is refused, exit 2" \
  sh -c '[ "$(cat "$1/sbad.rc")" = 2 ] && grep -qF "expected ollama or melious" "$1/sbad.err" && [ ! -e "$1/sbad.marks/codex-ran" ]' _ "$T"
run sseat SECOND_SEAT=melious bash "$SCRIPT" "$T/change.diff" --seat codex
check "sseat: --seat runs without SECOND_SEAT's model" \
  sh -c 'grep -qF "reviewers: codex OK" "$1/sseat.out" && [ "$(cat "$1/sseat.rc")" = 0 ]' _ "$T"
run sbadseat SECOND_SEAT=gpt bash "$SCRIPT" "$T/change.diff" --seat codex
check "sbadseat: a typo is refused under --seat too, exit 2" \
  sh -c '[ "$(cat "$1/sbadseat.rc")" = 2 ] && [ ! -e "$1/sbadseat.marks/codex-ran" ]' _ "$T"
run sbadlocal SECOND_SEAT=gpt OLLAMA_MODEL=stub-local bash "$SCRIPT" "$T/change.diff" --local-only
check "sbadlocal: a typo is refused under --local-only too, exit 2" \
  sh -c '[ "$(cat "$1/sbadlocal.rc")" = 2 ] && grep -qF "expected ollama or melious" "$1/sbadlocal.err" && [ ! -e "$1/sbadlocal.marks/ollama-ran" ]' _ "$T"
run sboth SECOND_SEAT=melious MELIOUS_MODEL=stub-melious MELIOUS_STUB=429 OLLAMA_STUB=429 bash "$SCRIPT" "$T/change.diff"
check "sboth: both seats refused, so the round is marked short" \
  sh -c 'grep -qF "reviewers: codex OK, melious FAILED (HTTP 429; quota/rate limit: wait or add credits), ollama-cloud FAILED" "$1" && grep -qF "fewer than the 2" "$1"' _ "$T/sboth.out"
# A reused raw dir: run 1's Melious OK must not stop run 2's fallback.
run sreuse1 SECOND_SEAT=melious MELIOUS_MODEL=stub-melious REVIEW_RAW_DIR="$T/sreuse.raw" bash "$SCRIPT" "$T/change.diff"
run sreuse2 SECOND_SEAT=melious MELIOUS_MODEL=stub-melious MELIOUS_STUB=429 REVIEW_RAW_DIR="$T/sreuse.raw" bash "$SCRIPT" "$T/change.diff"
check "sreuse: a stale Melious OK in a reused raw dir does not hold ollama back" \
  sh -c 'grep -qF "reviewers: codex OK, melious OK" "$1/sreuse1.out" && grep -qF "melious FAILED (HTTP 429" "$1/sreuse2.out" && [ -e "$1/sreuse2.marks/ollama-ran" ]' _ "$T"
# Stopping the script stops an ollama fallback started after Melious failed.
mkdir -p "$T/sstop.marks"
env -u CODEX_MODEL -u CODEX_EFFORT -u REVIEW_LOG -u XDG_STATE_HOME -u OLLAMA_API_KEY -u OLLAMA_TRANSPORT -u OLLAMA_MODEL -u OLLAMA_HOST -u AGY_MODEL -u MELIOUS_API_KEY -u MELIOUS_MAX_TOKENS -u MELIOUS_BASE_URL -u MELIOUS_ENV_FILE -u MELIOUS_API_TIMEOUT -u GIT_DIR -u GIT_WORK_TREE \
  PATH="$T/bin:$PATH" HOME="$T/u" WITH_ANTIGRAVITY=0 REVIEW_RAW_DIR="$T/sstop.raw" STUB_MARKS="$T/sstop.marks" STUB_TAG="$STUB_TAG" \
  CODEX_STUB=slow SECOND_SEAT=melious MELIOUS_MODEL=stub-melious MELIOUS_STUB=429 OLLAMA_STUB=stubborn \
  bash "$SCRIPT" "$T/change.diff" >"$T/sstop.out" 2>"$T/sstop.err" &
spid=$!
i=0; while [ ! -s "$T/sstop.marks/ollama-pid" ] && [ $i -lt 50 ]; do sleep 0.1; i=$((i+1)); done
kill -TERM "$spid"; wait "$spid"; echo $? >"$T/sstop.rc"
check "sstop: the script exits 130" rc_is sstop 130
check "sstop: the TERM-ignoring ollama fallback is gone" \
  sh -c 'p=$(cat "$1"); [ -n "$p" ] && case "$(ps -o stat= -p "$p" 2>/dev/null)" in ""|Z*) true ;; *) false ;; esac' _ "$T/sstop.marks/ollama-pid"
check "sstop: it was killed, not left to finish (a foreground fallback would finish)" [ ! -e "$T/sstop.marks/ollama-slept" ]
run slocal SECOND_SEAT=melious OLLAMA_MODEL=stub-local MELIOUS_MODEL=stub-melious bash "$SCRIPT" "$T/change.diff" --local-only
check "slocal: --local-only never calls Melious, whatever SECOND_SEAT says" \
  sh -c '! grep -qF melious "$1/slocal.out" && [ ! -e "$1/slocal.marks/melious-url" ]' _ "$T"

# 33. (2026-10-06) The Perl programs' minimum versions: check_perl_minimum.sh, which reads perl/*.pl
#     with Perl::MinimumVersion. It replaced the one-construct guards that stood here (no r-flag
#     substitution in the script) and in section 35 (no `//` in the ollama CLI filter).

# 34. #165 on top of the fallback: the key's sources and reach, the budget, the final-review marker
#     against leaked reasoning, think blocks anywhere, finish reasons, a reply cut off mid-stream.
MK=stub-melious-secret
run mbody MELIOUS_MODEL=stub-melious bash "$SCRIPT" "$T/change.diff" --seat melious
check "mbody: default budget 96000 and the final-review marker ask" \
  perl -MJSON::PP -e 'local $/; open my $f, "<", $ARGV[0] or exit 1; my $j = decode_json(<$f>); exit !($j->{max_tokens} == 96000 && $j->{messages}[0]{content} =~ /holds exactly === FINAL REVIEW [0-9a-f]{8,} ===/)' "$T/mbody.marks/melious-body"
check "mbody: no marker, small reply: kept whole, with the no-marker warning (round 16, melious)" sh -c 'grep -qF "melious OK" "$1" && grep -qF "no usable final-review marker" "$1" && ! grep -qF "text before the final-review marker dropped" "$1"' _ "$T/mbody.out"
run mbudget MELIOUS_MODEL=stub-melious MELIOUS_MAX_TOKENS=48000 MELIOUS_BASE_URL=https://example.test/v9/ bash "$SCRIPT" "$T/change.diff" --seat melious
check "mbudget: MELIOUS_MAX_TOKENS reaches the request" \
  perl -MJSON::PP -e 'local $/; open my $f, "<", $ARGV[0] or exit 1; exit !(decode_json(<$f>)->{max_tokens} == 48000)' "$T/mbudget.marks/melious-body"
check "mbudget: MELIOUS_BASE_URL, trailing slash dropped" grep -qxF "https://example.test/v9/chat/completions" "$T/mbudget.marks/melious-url"
run mbadbudget MELIOUS_MODEL=stub-melious MELIOUS_MAX_TOKENS=lots bash "$SCRIPT" "$T/change.diff" --seat melious
check "mbadbudget: a non-number budget fails before any call" sh -c 'grep -qF "melious FAILED (bad MELIOUS_MAX_TOKENS)" "$1" && [ ! -e "$2" ]' _ "$T/mbadbudget.out" "$T/mbadbudget.marks/melious-url"
run mkeyfall OLLAMA_STUB=429 MELIOUS_MODEL=stub-melious MELIOUS_API_KEY="$MK" STUB_KEY="$MK" bash "$SCRIPT" "$T/change.diff"
check "mkeyfall: codex never sees MELIOUS_API_KEY" test ! -e "$T/mkeyfall.marks/codex-saw-melious-key"
check "mkeyfall: melious still gets it, on stdin" grep -qxF "Authorization: Bearer $MK" "$T/mkeyfall.marks/melious-hdr"
check "mkeyfall: the key is not on curl's command line" not_in "$T/mkeyfall.marks/curl-argv-any" "$MK"
check "mkeyfall: the key is nowhere on disk during the call" test ! -e "$T/mkeyfall.marks/key-on-disk"
printf '%s\r\n' 'OTHER=1' "MELIOUS_API_KEY=\"file-key\"" 'MELIOUS_API_KEY=second-line' >"$T/melious.env"
run menv MELIOUS_MODEL=stub-melious MELIOUS_ENV_FILE="$T/melious.env" bash "$SCRIPT" "$T/change.diff" --seat melious
check "menv: the env file's first key line, quotes and CR dropped" grep -qxF "Authorization: Bearer file-key" "$T/menv.marks/melious-hdr"
printf 'export MELIOUS_API_KEY=keyendingr  \n' >"$T/melious2.env"
run menv2 MELIOUS_MODEL=stub-melious MELIOUS_ENV_FILE="$T/melious2.env" bash "$SCRIPT" "$T/change.diff" --seat melious
check "menv2: an export line works; trailing blanks dropped; a final r kept" grep -qxF "Authorization: Bearer keyendingr" "$T/menv2.marks/melious-hdr"
mkdir -p "$T/u/.config/reviewers"; printf 'MELIOUS_API_KEY=home-key\n' >"$T/u/.config/reviewers/melious.env"
run mhome MELIOUS_MODEL=stub-melious bash "$SCRIPT" "$T/change.diff" --seat melious
check "mhome: the default env file under HOME is read" grep -qxF "Authorization: Bearer home-key" "$T/mhome.marks/melious-hdr"
rm -f "$T/u/.config/reviewers/melious.env"
run mleak MELIOUS_MODEL=stub-melious MELIOUS_STUB=leak bash "$SCRIPT" "$T/change.diff" --seat melious
check "mleak: the answer after the LAST marker line is the review" sh -c 'grep -qF "reviewers: melious OK" "$1" && grep -qF "BUG: the real finding" "$1" && ! grep -qF "draft finding" "$1" && ! grep -qF "Let me think" "$1"' _ "$T/mleak.out"
check "mleak: the section says text was dropped" has mleak.out "text before the final-review marker dropped"
check "mleak: a usable marker gives no no-marker warning" lacks mleak.out "no usable final-review marker"
check "mleak: the untrimmed reply is kept in melious.full" grep -qF "Let me think" "$T/mleak.raw/melious.full"
run mleaknofull MELIOUS_MODEL=stub-melious MELIOUS_STUB=leaknofull bash "$SCRIPT" "$T/change.diff" --seat melious
check "mleaknofull: the note does not promise a melious.full it could not write" sh -c 'grep -qF "the full reply could not be saved" "$1" && ! grep -qF "is in melious.full" "$1" && grep -qF "BUG: the real finding" "$1"' _ "$T/mleaknofull.out"
run mbig MELIOUS_MODEL=stub-melious MELIOUS_STUB=bignomark bash "$SCRIPT" "$T/change.diff" --seat melious
check "mbig: a large reply without the marker is kept, with a warning" sh -c 'grep -qF "reviewers: melious OK" "$1" && grep -qF "this large reply may be leaked reasoning" "$1" && grep -qF "BUG: at the end" "$1"' _ "$T/mbig.out"
run mmarkdup MELIOUS_MODEL=stub-melious MELIOUS_STUB=markdup bash "$SCRIPT" "$T/change.diff" --seat melious
check "mmarkdup: a marker repeated at the end does not win" sh -c 'grep -qF "BUG: kept finding" "$1" && ! grep -qF "Thinking about it" "$1" && grep -qF "dropped, under 1 KB" "$1"' _ "$T/mmarkdup.out"
run mmarkfence MELIOUS_MODEL=stub-melious MELIOUS_STUB=markfence bash "$SCRIPT" "$T/change.diff" --seat melious
check "mmarkfence: a marker quoted in a fence after the review does not win" sh -c 'grep -qF "RISK: fenced case kept" "$1" && ! grep -qF "Thinking first" "$1"' _ "$T/mmarkfence.out"
run mmarkwrap MELIOUS_MODEL=stub-melious MELIOUS_STUB=markwrap bash "$SCRIPT" "$T/change.diff" --seat melious
check "mmarkwrap: a marker in bold is still found" sh -c 'grep -qF "BUG: wrapped marker kept" "$1" && ! grep -qF "Reasoning that leaked" "$1"' _ "$T/mmarkwrap.out"
run mbigmarkend MELIOUS_MODEL=stub-melious MELIOUS_STUB=bigmarkend bash "$SCRIPT" "$T/change.diff" --seat melious
check "mbigmarkend: markers but none usable, reply large: kept whole, with the warning" sh -c 'grep -qF "this large reply may be leaked reasoning" "$1" && grep -qF "BUG: at the end" "$1"' _ "$T/mbigmarkend.out"
run mglued MELIOUS_MODEL=stub-melious MELIOUS_STUB=glued bash "$SCRIPT" "$T/change.diff" --seat melious
check "mglued: a marker glued to the end of a reasoning line still cuts there (round 16c, melious)" sh -c 'grep -qF "BUG: the real finding" "$1" && ! grep -qF "Thinking it over" "$1" && grep -qF "text before the final-review marker dropped" "$1"' _ "$T/mglued.out"
check "mglued: a cut at a glued marker says so" grep -qF "the marker ended a line of other text" "$T/mglued.out"
run mechoglued MELIOUS_MODEL=stub-melious MELIOUS_STUB=echoglued bash "$SCRIPT" "$T/change.diff" --seat melious
check "mechoglued: reasoning that restates the marker on a line of its own, then glues the real one: cut at the glued one, and said" sh -c 'grep -qF "BUG: the real finding" "$1" && ! grep -qF "More reasoning" "$1" && grep -qF "the marker ended a line of other text" "$1"' _ "$T/mechoglued.out"
run mfencequote MELIOUS_MODEL=stub-melious MELIOUS_STUB=fencequote bash "$SCRIPT" "$T/change.diff" --seat melious
check "mfencequote: a finding that quotes the marker in a fence does not cut the findings above it" sh -c 'grep -qF "BUG: real finding one" "$1" && grep -qF "NIT: three" "$1" && ! grep -qF "marker dropped" "$1"' _ "$T/mfencequote.out"
run mafterfence MELIOUS_MODEL=stub-melious MELIOUS_STUB=afterfence bash "$SCRIPT" "$T/change.diff" --seat melious
check "mafterfence: the real marker skipped as quoted, an earlier one used: the findings are kept and the cut is flagged" sh -c 'grep -qF "BUG: the real finding" "$1" && grep -qF "the marker came 2 times with findings after it, so check that the section starts with the review" "$1"' _ "$T/mafterfence.out"
run mindentquote MELIOUS_MODEL=stub-melious MELIOUS_STUB=indentquote bash "$SCRIPT" "$T/change.diff" --seat melious
check "mindentquote: a quote the rules miss moves the cut, and the cut is flagged" grep -qF "so check that the section starts with the review" "$T/mindentquote.out"
run mtopecho MELIOUS_MODEL=stub-melious MELIOUS_STUB=topecho bash "$SCRIPT" "$T/change.diff" --seat melious
check "mtopecho: a cut at the very top with another usable marker below is still flagged" sh -c 'grep -qF "BUG: the real finding" "$1" && grep -qF "the final-review marker came 2 times with findings after it, so check that the section starts with the review" "$1"' _ "$T/mtopecho.out"
run mquotemark MELIOUS_MODEL=stub-melious MELIOUS_STUB=quotemark bash "$SCRIPT" "$T/change.diff" --seat melious
check "mquotemark: a finding that quotes the marker at its line end does not cut the findings above it" sh -c 'grep -qF "BUG: real finding one" "$1" && grep -qF "NIT: three" "$1" && ! grep -qF "marker dropped" "$1" && ! grep -qF "no usable final-review marker" "$1"' _ "$T/mquotemark.out"
run moldmark MELIOUS_MODEL=stub-melious MELIOUS_STUB=oldmark bash "$SCRIPT" "$T/change.diff" --seat melious
check "moldmark: a reply quoting the old fixed marker: only this run's marker counts" sh -c 'grep -qF "BUG: the real finding" "$1" && ! grep -qF "a draft that quotes" "$1" && grep -qF "text before the final-review marker dropped" "$1"' _ "$T/moldmark.out"
# The marker is never one the reviewed text holds, even when the random source repeats itself.
mkdir -p "$T/odbin"; printf '#!/bin/sh\nprintf " de ad be ef\\n"\n' >"$T/odbin/od"; chmod +x "$T/odbin/od"
printf 'diff --git a/x b/x\n+=== FINAL REVIEW deadbeef ===\n+=== FINAL REVIEW deadbeefdeadbeef ===\n' >"$T/markdiff.diff"
run mcollide MELIOUS_MODEL=stub-melious MELIOUS_STUB=markend PATH="$T/odbin:$T/bin:$PATH" bash "$SCRIPT" "$T/markdiff.diff" --seat melious
check "mcollide: markers the diff holds are skipped, even from a stuck random source" sh -c 'grep -qF "holds exactly === FINAL REVIEW deadbeefdeadbeefdeadbeef ===" "$1" && grep -qF "reviewers: melious OK" "$2"' _ "$T/mcollide.marks/melious-body" "$T/mcollide.out"
run mbody2 MELIOUS_MODEL=stub-melious bash "$SCRIPT" "$T/change.diff" --seat melious
check "mbody2: each run asks for a marker of its own" sh -c 'a=$(grep -o "FINAL REVIEW [0-9a-f]* ===" "$1" | head -n 1); b=$(grep -o "FINAL REVIEW [0-9a-f]* ===" "$2" | head -n 1); [ -n "$a" ] && [ -n "$b" ] && [ "$a" != "$b" ]' _ "$T/mbody.marks/melious-body" "$T/mbody2.marks/melious-body"
run mmarkend MELIOUS_MODEL=stub-melious MELIOUS_STUB=markend bash "$SCRIPT" "$T/change.diff" --seat melious
check "mmarkend: a marker with nothing after it: the reply is kept whole" sh -c 'grep -qF "reviewers: melious OK" "$1" && grep -qF "BUG: before the marker" "$1"' _ "$T/mmarkend.out"
run mthinkonly MELIOUS_MODEL=stub-melious MELIOUS_STUB=thinkonly bash "$SCRIPT" "$T/change.diff" --seat melious
check "mthinkonly: a reply that is only thinking has no review text" sh -c 'grep -qF "melious FAILED (HTTP 200 but no review text)" "$1" && grep -qF "the reply holds no text, only thinking" "$1"' _ "$T/mthinkonly.out"
run mthinklast MELIOUS_MODEL=stub-melious MELIOUS_STUB=thinklast bash "$SCRIPT" "$T/change.diff" --seat melious
check "mthinklast: a think block after the review is dropped, the review kept" sh -c 'grep -qF "reviewers: melious OK" "$1" && grep -qF "BUG: kept before" "$1" && ! grep -qF "trailing thoughts" "$1"' _ "$T/mthinklast.out"
run munclosed MELIOUS_MODEL=stub-melious MELIOUS_STUB=unclosed bash "$SCRIPT" "$T/change.diff" --seat melious
check "munclosed: an opener never closed: the rest is thinking and is dropped" sh -c 'grep -qF "reviewers: melious OK" "$1" && grep -qF "BUG: kept first" "$1" && ! grep -qF "could not read" "$1"' _ "$T/munclosed.out"
check "mthinklast: and says what it cut" has mthinklast.out "think block text dropped"
run mquotedtag MELIOUS_MODEL=stub-melious MELIOUS_STUB=quotedtag bash "$SCRIPT" "$T/change.diff" --seat melious
check "mquotedtag: a tag quoted inside a finding cuts nothing (re-gate, fresh-eyes)" sh -c 'grep -qF "melious OK" "$1" && grep -qF "NIT: keep this line" "$1" && ! grep -qF "think block text dropped" "$1"' _ "$T/mquotedtag.out"
run moddfinish MELIOUS_MODEL=stub-melious MELIOUS_STUB=oddfinish bash "$SCRIPT" "$T/change.diff" --seat melious
check "moddfinish: a finish_reason carrying 429 text is not read as quota" sh -c 'grep -qF "melious FAILED (truncated review (HTTP 200))" "$1" && ! grep -qF "quota/rate limit" "$1" && ! grep -qF "finish_reason 429" "$1"' _ "$T/moddfinish.out"
run mfilter MELIOUS_MODEL=stub-melious MELIOUS_STUB=filter bash "$SCRIPT" "$T/change.diff" --seat melious
check "mfilter: a finish other than stop is a truncated review" sh -c 'grep -qF "melious FAILED (truncated review (HTTP 200))" "$1" && grep -qF "finish_reason content_filter" "$1"' _ "$T/mfilter.out"
run mlengthbudget MELIOUS_MODEL=stub-melious MELIOUS_STUB=length bash "$SCRIPT" "$T/change.diff" --seat melious
check "mlengthbudget: a reply cut by the budget names the knob" has mlengthbudget.out "raise MELIOUS_MAX_TOKENS"
check "mlengthbudget: the raw reply is saved on a failure path too" grep -qF "cut off" "$T/mlengthbudget.raw/melious.full"
run mreset MELIOUS_MODEL=stub-melious MELIOUS_STUB=reset bash "$SCRIPT" "$T/change.diff" --seat melious
check "mreset: a reply that broke off is named as such" has mreset.out "reviewers: melious FAILED (curl exit 56, reply cut off)"
check "mreset: ...not as a blocked host" sh -c '! grep -qF "network policy" "$1"' _ "$T/mreset.out"
check "mreset: ...and the part that came is kept" grep -qF "half a reply" "$T/mreset.raw/melious.resp"
run mstale MELIOUS_MODEL=stub-melious bash "$SCRIPT" "$T/change.diff" --seat melious
run mstale2 MELIOUS_MODEL=stub-melious MELIOUS_STUB=nousage REVIEW_RAW_DIR="$T/mstale.raw" bash "$SCRIPT" "$T/change.diff" --seat melious
check "mstale: the first run counted its tokens" grep -qE '^timings: melious [0-9]+s \(600 tokens\)$' "$T/mstale.out"
check "mstale2: a reused raw dir does not lend it the old count, nor the old melious.full" \
  sh -c 'grep -qE "^timings: melious [0-9]+s$" "$1" && ! grep -qF "melious finding one" "$2"' _ "$T/mstale2.out" "$T/mstale.raw/melious.full"

# Real curl, not the stub: the key reaches curl only through `-H @-` (stdin), and the stub
# implements that itself, so it cannot prove real curl honours it (round 5, melious). A local
# server records the Authorization header of a keyed call and of a keyless one.
REAL_CURL="$(command -v curl || true)"
# python3 must be able to serve, not merely exist (a stock Mac's /usr/bin/python3 can be a stub).
if [ -n "$REAL_CURL" ] && command -v python3 >/dev/null 2>&1 && python3 -c 'import http.server' >/dev/null 2>&1; then
  echo "real-curl cases: curl $REAL_CURL, python3 $(command -v python3) ($(python3 -c 'import sys; print(sys.version.split()[0])'))"
  cat >"$T/echo.py" <<'PY'
import http.server, sys
class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        with open(sys.argv[2], "a") as f:
            f.write("auth=%s\n" % self.headers.get("Authorization"))
        self.send_response(200); self.end_headers()
        if self.path.endswith("/api/chat"):   # the ollama API: NDJSON
            self.wfile.write(b'{"message":{"content":"- BUG: real curl ollama\\n- NIT: two"},"done":false}\n'
                             b'{"message":{"content":""},"done":true,"prompt_eval_count":5,"eval_count":5}\n')
        else:                                 # melious: server-sent events
            self.wfile.write(b'data: {"choices":[{"index":0,"delta":{"content":"- BUG: real curl\\n- NIT: two"}}]}\n\n'
                             b'data: {"choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n')
    def log_message(self, *a): pass
# HTTPServer's own server_bind asks socket.getfqdn() for the host's name: a reverse DNS
# lookup that can stall for many seconds on a macOS runner (macos-stock-tools: no port
# file in 10 s, nothing on stderr). Bind without it.
import os, socketserver
class S(http.server.HTTPServer):
    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = "127.0.0.1", self.server_address[1]
s = S(("127.0.0.1", 0), H)
with open(sys.argv[1] + ".tmp", "w") as f:
    f.write(str(s.server_address[1]))
os.replace(sys.argv[1] + ".tmp", sys.argv[1])   # the port file appears whole, or not at all
for _ in range(3): s.handle_request()
PY
  python3 "$T/echo.py" "$T/echo.port" "$T/echo.log" 2>"$T/echo.err" & echo_pid=$!
  i=0; while [ ! -s "$T/echo.port" ] && [ $i -lt 300 ]; do sleep 0.1; i=$((i+1)); done
  if [ ! -s "$T/echo.port" ]; then
    echo "real-curl cases: the local server wrote no port in 30 s; its stderr:"; sed 's/^/    /' "$T/echo.err"
    kill -0 "$echo_pid" 2>/dev/null && echo "    (the server process is still running)" || echo "    (the server process has exited)"
    # One clear failure, not six curl errors against an empty port (round 8, melious).
    echo "FAIL real-curl cases: no local server, so none of them ran"; fails=$((fails+1))
  else
    RC_PATH="$(dirname "$REAL_CURL"):/usr/bin:/bin"
    run mreal PATH="$RC_PATH" NO_PROXY=127.0.0.1 no_proxy=127.0.0.1 MELIOUS_MODEL=stub-m MELIOUS_API_KEY=real-curl-key \
      MELIOUS_BASE_URL="http://127.0.0.1:$(cat "$T/echo.port")/v1" bash "$SCRIPT" "$T/change.diff" --seat melious
    run mrealnokey PATH="$RC_PATH" NO_PROXY=127.0.0.1 no_proxy=127.0.0.1 MELIOUS_MODEL=stub-m \
      MELIOUS_BASE_URL="http://127.0.0.1:$(cat "$T/echo.port")/v1" bash "$SCRIPT" "$T/change.diff" --seat melious
    run oreal PATH="$RC_PATH" NO_PROXY=127.0.0.1 no_proxy=127.0.0.1 OLLAMA_TRANSPORT=api OLLAMA_MODEL=stub-local \
      OLLAMA_HOST="127.0.0.1:$(cat "$T/echo.port")" OLLAMA_API_KEY=real-ollama-key bash "$SCRIPT" "$T/change.diff" --seat ollama
    check "mreal: real curl, keyed: counted" has mreal.out "reviewers: melious OK"
    check "mreal: real curl sends the stdin header" grep -qxF "auth=Bearer real-curl-key" "$T/echo.log"
    check "mrealnokey: real curl with an empty stdin header list: counted" has mrealnokey.out "reviewers: melious OK"
    check "mrealnokey: ...and sends no Authorization at all" grep -qxF "auth=None" "$T/echo.log"
    check "oreal: real curl, ollama API: the stdin header arrives" grep -qxF "auth=Bearer real-ollama-key" "$T/echo.log"
    check "oreal: ...and the review is read" has oreal.out "- BUG: real curl ollama"
  fi
  kill "$echo_pid" 2>/dev/null; wait "$echo_pid" 2>/dev/null
else
  echo "SKIP: the real-curl cases need curl and a python3 that can import http.server. The -H @- path was NOT checked against real curl."
fi

# 35. A Perl older than 5.10 (2026-10-06). The API transports need 5.10 and check for it before
#     sending anything, so they are skipped. The CLI transport has no version check, so its output
#     filter (perl/ollama_filter.pl) must stay within 5.8: check_perl_minimum.sh holds it there. A
#     wrapper perl fails exactly the `require 5.010` probe (one argument, nothing else in it),
#     leaves a mark when it does, and runs the real perl otherwise.
REALPERL="$(command -v perl)"
mkdir -p "$T/oldperl"
cat >"$T/oldperl/perl" <<EOF
#!/bin/sh
for a; do case "\$a" in 'require 5.010') : >"\$STUB_MARKS/perl510-refused"; echo "Perl v5.10.0 required--this is only v5.8.9" >&2; exit 2 ;; esac; done
exec "$REALPERL" "\$@"
EOF
chmod +x "$T/oldperl/perl"
run oldcli PATH="$T/oldperl:$T/bin:$PATH" bash "$SCRIPT" "$T/change.diff"
check "oldcli: an old Perl still runs the ollama CLI tier, it counts, and no version probe ran" \
  sh -c 'grep -qF "reviewers: codex OK, ollama-cloud OK" "$1/oldcli.out" && [ -e "$1/oldcli.marks/ollama-ran" ] && [ ! -e "$1/oldcli.marks/perl510-refused" ]' _ "$T"
run oldapi PATH="$T/oldperl:$NOCLI" OLLAMA_MODEL="$STUB_TAG" MELIOUS_MODEL=stub-melious bash "$SCRIPT" "$T/change.diff"
check "oldapi: an old Perl skips the ollama API and Melious tiers, says why, nothing sent" \
  sh -c 'grep -qF "ollama-cloud SKIPPED (Perl 5.10 or newer not found), melious SKIPPED (Perl 5.10 or newer not found)" "$1/oldapi.out" && [ ! -e "$1/oldapi.marks/curl-url" ] && [ ! -e "$1/oldapi.marks/melious-url" ] && [ -e "$1/oldapi.marks/perl510-refused" ]' _ "$T"

# 36. The API transports' other missing tools are named in the summary too: a Perl without
#     JSON::PP (a wrapper perl fails exactly the module probe), and no curl or no perl at all.
mkdir -p "$T/nojsonperl"
cat >"$T/nojsonperl/perl" <<EOF
#!/bin/sh
if [ "\$#" = 3 ] && [ "\$1" = -MJSON::PP ] && [ "\$2" = -e ] && [ "\$3" = 1 ]; then
  : >"\$STUB_MARKS/jsonpp-refused"; echo "Can't locate JSON/PP.pm in @INC" >&2; exit 2
fi
exec "$REALPERL" "\$@"
EOF
chmod +x "$T/nojsonperl/perl"
run nojson PATH="$T/nojsonperl:$NOCLI" OLLAMA_MODEL="$STUB_TAG" MELIOUS_MODEL=stub-melious bash "$SCRIPT" "$T/change.diff"
check "nojson: no JSON::PP: both API tiers skipped, the module named, nothing sent" \
  sh -c 'grep -qF "ollama-cloud SKIPPED (Perl module JSON::PP not found), melious SKIPPED (Perl module JSON::PP not found)" "$1/nojson.out" && [ ! -e "$1/nojson.marks/curl-url" ] && [ ! -e "$1/nojson.marks/melious-url" ] && [ -e "$1/nojson.marks/jsonpp-refused" ]' _ "$T"
# A PATH of links to every tool in /usr/bin and /bin, less one: two ln calls, not one per file.
# The ollama API transport is pinned, so an ollama CLI on the host cannot change the path taken.
mkdir -p "$T/bin3"; cp "$T/bin/codex" "$T/bin3/"
for drop in curl perl; do
  mkdir -p "$T/no$drop"; ln -s /usr/bin/* "$T/no$drop/" 2>/dev/null; ln -s /bin/* "$T/no$drop/" 2>/dev/null; rm -f "$T/no$drop/$drop"
done
run nocurl PATH="$T/bin3:$T/nocurl" OLLAMA_TRANSPORT=api OLLAMA_MODEL="$STUB_TAG" MELIOUS_MODEL=stub-melious bash "$SCRIPT" "$T/change.diff"
check "nocurl: no curl: both API tiers skipped, curl named" \
  has nocurl.out "reviewers: codex OK, ollama-cloud SKIPPED (curl not found), melious SKIPPED (curl not found)"
run noperl PATH="$T/bin3:$T/noperl" OLLAMA_TRANSPORT=api OLLAMA_MODEL="$STUB_TAG" MELIOUS_MODEL=stub-melious bash "$SCRIPT" "$T/change.diff"
check "noperl: no perl at all: named as missing, not as too old" \
  has noperl.out "ollama-cloud SKIPPED (perl not found), melious SKIPPED (perl not found)"

# 37. (2026-10-09) Past round 8 the script prints a notice and nothing else changes (SKILL.md step 6):
#     the exit code, the reviewers line and the cost log's outcome column are as at round 8. A
#     13-round gate had no owner decision recorded past round 8; a refusal would stop the process,
#     so this is a line the caller reads in the round's own output.
run round8 REVIEW_LOG="$T/round8.tsv" bash "$SCRIPT" "$T/change.diff" --depth normal --round 8
run round9 REVIEW_LOG="$T/round9.tsv" bash "$SCRIPT" "$T/change.diff" --depth normal --round 9
run round12 bash "$SCRIPT" "$T/change.diff" --depth normal --round 12
run noround bash "$SCRIPT" "$T/change.diff"
check "round 8: no past-round-8 notice" lacks round8.out "is past round 8"
check "round 9: the notice names the round, the step and the owner" \
  has round9.out "⚠ Round 9 is past round 8 (SKILL.md step 6): each round from here on is the owner's decision, one at a time."
check "round 9: the notice also reaches stderr" has round9.err "Round 9 is past round 8"
check "round 9: exit code as at round 8" [ "$(cat "$T/round9.rc")" = "$(cat "$T/round8.rc")" ]
check "round 9: the reviewers line is the one round 8 prints" \
  sh -c 'a="$(grep "^reviewers:" "$1/round9.out")"; [ -n "$a" ] && [ "$a" = "$(grep "^reviewers:" "$1/round8.out")" ]' _ "$T"
check "round 9: the cost log's outcome column is as at round 8, and says OK" \
  sh -c 'a="$(awk -F"\t" "NR>1{print \$13}" "$1/round9.tsv")"; [ -n "$a" ] && [ "$a" = "$(awk -F"\t" "NR>1{print \$13}" "$1/round8.tsv")" ] && ! printf "%s" "$a" | grep -qv OK' _ "$T"
check "round 12: a two-digit round gets the notice" has round12.out "⚠ Round 12 is past round 8"
check "no --round: no notice (a limit; SKILL.md step 6 still applies)" lacks noround.out "is past round 8"

if [ $fails -ne 0 ]; then echo "$fails check(s) FAILED"; exit 1; fi
echo "all checks passed"
