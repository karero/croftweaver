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
| 1 | Codex (base `69e1da98`, head `451abbe6`) | 0 / 1 / 0 | the note said the spec needs the file `src/styles/tables.css`; it only checks table behaviour, so equivalent styles may do |
| 1 | fresh-eyes (Sonnet subagent, read-only) | 0 / 0 / 2 | the note did not write out the `left_out:` line's format; the "spec still names" check is a loose proxy |
| 2 | Codex (`--verify`, base `451abbe6`, head `2e511904`) | 0 / 0 / 0 | both fixes landed; no new finding |

Tokens and time: round 1 Codex 44,073 (86 s); fresh-eyes 102,726 (60 s); round 2 Codex 37,224 (73 s). Codex alone
(REVIEW-RULES); the script's warning that the standard pair was not met applies.

## Findings

| Id | Sev | Source | Finding | Status |
|---|---|---|---|---|
| R1-01 | RISK | Codex | "needs `src/styles/tables.css`" overstates what the spec checks | fixed: the note says the spec "expects `THEMES` in `tests/_helpers.ts` and the starter's table styles (`src/styles/tables.css`, imported in the layout)"; S14 checks the new words; verified clean in round 2 |
| F-01 | NIT | fresh-eyes | the note named a `left_out:` line without its format (README: `left_out: <path> — <why>`) | fixed: the note writes `left_out: tests/tables.spec.ts — <why>`; S14 checks it |
| F-02 | NIT | fresh-eyes | S14's "spec still names THEMES and tables.css" matches a word anywhere in the spec | left: a proxy by design, as S13's is; it still fails if both words go (Codex reproduced that in round 2) |

Codex listed the PR number in the BUGLOG status and the two sites' conditions as unverifiable. The status names the number the
PR gets; it is checked when the PR is opened. The sites' conditions are the row's own account (a site whose `_helpers.ts`
lacks `THEMES`, a site without the CSS), and the note says "a site without them", not which sites.

## Test evidence

- `bash scripts/test_whats_new.sh` at `451abbe6` with the fix: exit 0, new case S14 9 lines ok. The old `whats-new.sh`
  restored by hand: exit 1, 4 FAIL lines (the note lacks `THEMES in tests/_helpers.ts`, `src/styles/tables.css`, `leave it
  out on purpose`, `left_out:`), "4 test(s) failed". At `2e511904` (the round-1 fixes): exit 0, S14 all ok. S14 runs the
  real script on a throwaway suite and site, the way an owner does.
- `make check`: a first run was stopped before it ended, to apply the round-1 fixes (nothing of it counts). The run that
  counts is the one after this trail's last edit; its result is in the PR.
