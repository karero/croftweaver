# DIFF review — bug sweep 7 of 2026-11-23 (one BUGLOG row)

Base `69e1da98` (origin/main) · depth: Normal (a shipped script, so not Light) · seat: Codex alone (REVIEW-RULES; no
High-row topic) · fresh-eyes: a read-only subagent at round 1 (this session's own). Artifact: the whole diff against
the base, with a brief holding the test records as evidence.

Sweep 7 read every open row. One qualified, and the manager asked for a one-row PR: `whats-new.sh`, the gap report for
`tests/tables.spec.ts` (2026-11-16). Checked on `main` first: `workers-config.spec.ts` had a note arm, `tables.spec.ts`
had none, so a dark-only site or one without `src/styles/tables.css` read "MISSING" with no way on. The rows left, and why,
are in the session's notes.

| Round | Reviewers | BUG / RISK / NIT | What came back |
|---|---|---|---|
| 1 | (to fill) | | |

## Test evidence

- `bash scripts/test_whats_new.sh`: all passed with the fix (new case S14: 9 lines ok). The old `whats-new.sh` restored by
  hand: exit 1, 4 FAIL lines ("the note lacks: THEMES in tests/_helpers.ts", "src/styles/tables.css", "leave it out on
  purpose", "left_out:"), "4 test(s) failed". S14 runs the real script on a throwaway suite and site, the way an owner does.
- `make check`: (to fill)
