#!/usr/bin/env bash
# sweep_claims.sh — before round 1 of a prose gate, list every sentence the change ADDS
# that asserts an absence or a universal ("has not been attempted", "never", "only",
# "first"), so the author can check each against the record. Advisory: it prints
# candidates and exits 0; 2 means a usage error. When and how to use the list:
# references/claims-sweep.md. The work is in sweep_claims.py; this launcher exists so a
# machine without python3 gets one line and exit 0 instead of a failed step.
#
# Usage: sweep_claims.sh --base REF [--head REF | --worktree] [--repo DIR] [PATH ...]
#        sweep_claims.sh --file PATH [--file PATH ...]
#        sweep_claims.sh --help
if ! command -v python3 >/dev/null 2>&1; then
  echo "sweep_claims: python3 not found, so the claims sweep was skipped (it is advisory; the review can go on)." >&2
  exit 0
fi
# CDPATH= keeps an exported CDPATH from sending cd somewhere else, or printing where it went.
exec python3 "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/sweep_claims.py" "$@"
