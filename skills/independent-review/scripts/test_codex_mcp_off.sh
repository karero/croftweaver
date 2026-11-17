#!/usr/bin/env bash
#
# test_codex_mcp_off.sh — drives independent_review.sh --seat codex the way a caller does, with a
# stub `codex` first on PATH and HOME relocated, and checks that the Codex seat turns off the MCP
# servers `codex mcp list --json` names, for that run only, and that a list it cannot get leaves
# the run as it was, with a note on stderr. No reviewer is contacted.
#
# Why it exists: every Codex review started the servers in the user's Codex config (a browser
# driver, a JavaScript runner) though a review uses none, at about 130 MB and 2.8 s CPU a run and
# beside the reviewed text. Plan: docs/reviews/SKILL-PLAN-review-codex-no-mcp.md (T1).
# The first case reads a trimmed real capture (fixtures/codex-cli-0.169.0_2026-11-17_mcp-list.json:
# two enabled servers, one disabled); the expected values below are written by hand.
#
# Needs perl with JSON::PP. Usage: bash skills/independent-review/scripts/test_codex_mcp_off.sh
set -u
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
SCRIPT="$HERE/independent_review.sh"
command -v perl >/dev/null 2>&1 || { echo "SKIP test_codex_mcp_off.sh — perl not found"; exit 0; }
perl -MJSON::PP -e 1 2>/dev/null || { echo "SKIP test_codex_mcp_off.sh — Perl module JSON::PP not found"; exit 0; }
T="$(mktemp -d "${TMPDIR:-/tmp}/ir-mcp-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
trap 'rm -rf "$T"' EXIT
T="$(CDPATH= cd -- "$T" && pwd -P)"
mkdir -p "$T/bin" "$T/u/.codex" "$T/work"
: >"$T/u/.codex/auth.json"
printf 'model = "stub-codex"\n' >"$T/u/.codex/config.toml"
printf '# Plan\n\nStep 1: do the thing.\n' >"$T/plan.md"
# `mcp list` answers as MCP_STUB says and records its argv and folder; anything else is `exec`,
# which records its argv (the prompt comes on stdin, the last argument is "-") and folder.
cat >"$T/bin/codex" <<'EOF'
#!/bin/sh
if [ "${1:-}" = mcp ]; then
  printf 'argv=%s cwd=%s\n' "$*" "$(pwd -P)" >>"$STUB_MARKS/mcp-calls"
  case "${MCP_STUB:-real}" in
    real)  cat "$STUB_FIXTURE" ;;
    empty) printf '%s\n' '[]' ;;
    dotted) printf '%s\n' '[{"name":"a.b","enabled":true},{"name":"ok-1","enabled":true}]' ;;
    fail)  echo 'Error: Unknown feature flag: plugins' >&2; exit 1 ;;
    slow)  sleep 60 ;;
  esac
  exit 0
fi
argv=; for a; do argv="$argv[$a]"; done
cat >/dev/null
printf 'argv=%s cwd=%s\n' "$argv" "$(pwd -P)" >"$STUB_MARKS/codex-args"
printf '%s\n' '- BUG: stub finding one' '- NIT: stub finding two'
EOF
chmod +x "$T/bin/codex"
export HOME="$T/u"

fails=0
check() {   # check <description> <command ...>
  if "${@:2}"; then printf 'ok   %s\n' "$1"; else printf 'FAIL %s\n' "$1"; fails=$((fails+1)); fi
}
has()   { grep -qF -- "$2" "$T/$1"; }
lacks() { ! grep -qF -- "$2" "$T/$1"; }
# run <name> <MCP_STUB value> — runs from $T/work, leaves $T/<name>.out, .err, .rc and marks/<name>
run() {
  local name="$1"; mkdir -p "$T/marks/$name"
  ( cd "$T/work" && env -u CODEX_MODEL -u CODEX_EFFORT -u OLLAMA_MODEL -u MELIOUS_MODEL -u SECOND_SEAT \
      PATH="$T/bin:$PATH" WITH_ANTIGRAVITY=0 REVIEW_LOG=off MCP_STUB="$2" STUB_MARKS="$T/marks/$name" \
      STUB_FIXTURE="$HERE/fixtures/codex-cli-0.169.0_2026-11-17_mcp-list.json" \
      REVIEW_RAW_DIR="$T/raw.$name" bash "$SCRIPT" "$T/plan.md" --plan --seat codex --depth normal \
      >"$T/$name.out" 2>"$T/$name.err"; echo $? >"$T/$name.rc" )
}
exec_args() { sed -e 's/^argv=//' -e 's/ cwd=.*$//' "$T/marks/$1/codex-args"; }
counted()   { [ "$(cat "$T/$1.rc")" = 0 ] && has "$1.out" "## Independent review — codex (stub-codex, read-only)"; }
base='[exec][-s][read-only][--skip-git-repo-check][-c][project_doc_max_bytes=0][-c][skills.include_instructions=false]'

# The slow case waits out the 20-second bound: start it first, read it last.
run slow slow &
slow_pid=$!

# (a) two enabled servers, one disabled (the real capture): both off, in the place the plan names.
run real real
check "a: exact exec argv: --disable plugins, then one -c per enabled server, in list order" \
  [ "$(exec_args real)" = "$base[--disable][plugins][-c][mcp_servers.chrome-devtools.enabled=false][-c][mcp_servers.node_repl.enabled=false][-]" ]
check "a: the list was asked for once, with plugins off, in the folder exec runs in" \
  [ "$(cat "$T/marks/real/mcp-calls")" = "argv=mcp list --json --disable plugins cwd=$T/work" ]
check "a: exec ran in that same folder" has "marks/real/codex-args" " cwd=$T/work"
check "a: the review section still counts" counted real
check "a: no MCP note on stderr" lacks real.err "MCP server"

# (b) the list fails: the argv is today's, and stderr says why.
run fail fail
check "b: exec argv exactly as before" [ "$(exec_args fail)" = "$base[-]" ]
check "b: stderr says the servers were left on, and why" \
  has fail.err "codex: MCP servers left on (listing them failed (exit 1: Error: Unknown feature flag: plugins))"
check "b: the review section still counts" counted fail

# (c) a name that is not a plain key: named on stderr, the other still goes off.
run dotted dotted
check "c: only the plain name is passed" \
  [ "$(exec_args dotted)" = "$base[--disable][plugins][-c][mcp_servers.ok-1.enabled=false][-]" ]
check "c: stderr names the one that stays on" has dotted.err 'codex: MCP server "a.b" stays on'
check "c: the review section still counts" counted dotted

# (e) no servers: plugins off, no -c, no note.
run empty empty
check "e: --disable plugins, no -c" [ "$(exec_args empty)" = "$base[--disable][plugins][-]" ]
check "e: no MCP note on stderr" lacks empty.err "MCP server"
check "e: the review section still counts" counted empty

# (d) the list sleeps past the bound.
wait "$slow_pid"
check "d: exec argv exactly as before" [ "$(exec_args slow)" = "$base[-]" ]
check "d: stderr says the listing timed out" has slow.err "codex: MCP servers left on (listing them timed out after 20 seconds)"
check "d: the review section still counts" counted slow

if [ "$fails" -gt 0 ]; then echo "$fails check(s) failed"; exit 1; fi
echo "all checks passed"
