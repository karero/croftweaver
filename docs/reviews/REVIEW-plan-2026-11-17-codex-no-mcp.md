# PLAN review — branch `plan/codex-review-no-mcp` — Codex review runs start no MCP servers

Plan: `docs/reviews/SKILL-PLAN-review-codex-no-mcp.md`. Evidence sent every round with
`--evidence`: `docs/reviews/evidence-codex-no-mcp/measurements.md`. Depth: Normal (a plan for the
review tool; it only removes tools from a read-only run, so no High-row item and no red team).
Seats: Codex and GLM 5.3 on melious, per the seat rules for plans, plus fresh-eyes (Sonnet) in
round 1. Melious was out of balance ("Insufficient balance for request"), so the round stands on
Codex alone; by the owner's rule (2026-10-27) no rerun of melious is owed. Gate id
`20261117T164109Z-71268`. This session (codex-review-no-mcp) created the worktree, the branch and
every commit.

Checks before round 1: `scripts/check_clean.sh` passed. The change adds files under
`docs/reviews/` only; the full `make check` runs in CI on the PR.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|-------|------|----------|-----------|-----------------|--------------|
| 1 | `dceaba41` | the whole plan | Codex; melious out of balance; fresh-eyes (Sonnet) | Codex 159 s, 63,485; fresh-eyes 57 s, 115,230 | 3 / 6 / 3 |

## Round 1 findings

| Id | Seat | Sev | Finding | Disposition |
|----|------|-----|---------|-------------|
| A1 | Codex | BUG | "turns them all off" contradicts the steps that leave a server on | fixed: What says every server it can name goes off; one it cannot is named on stderr |
| A2 | Codex | BUG | Answering `[]` still changes the exact argv pinned in `test_failed_tier_report.sh` (no-git case, §26) | fixed: the plan names both pins and the `[--disable][plugins]` they gain |
| A3 | Codex | BUG | "starts every MCP server" though the evidence lists two disabled ones | fixed: "every enabled MCP server" |
| A4 | Codex | RISK | The second `mcp list` had no time bound | fixed by F2: the second list is dropped |
| A5 | Codex | RISK | T1 not registered in `Makefile` and `clean.yml` | fixed: Wiring bullet names both |
| A6 | Codex | RISK | New files not placed in `check_perl_minimum.sh`, `check_cdpath_safe.sh`, `test_mktemp_guard.sh` | fixed: Wiring bullet names them and `package.sh` |
| F1 | fresh-eyes | RISK | The stubs record marks and refuse a non-git dir before any case: an `mcp list` branch is not a one-liner | fixed: the branch goes on each stub's first line and exits before any mark or check |
| F2 | fresh-eyes | RISK | The second list reads the same config view as the first, so it cannot show what `exec` starts | fixed: dropped, with the reason under Not adopted; the live check is the proof |
| F3 | fresh-eyes | RISK | List and `exec` might differ for a project's own `.codex/config.toml` | fixed: named under Not covered |
| F4 | fresh-eyes | NIT | A dotted name stops Codex; quoting was not tested | fixed: step 3 cites the check |
| F5 | fresh-eyes | NIT | "every doc that lists the flags" not checkable | fixed: the two docs are named |
| F6 | fresh-eyes | NIT | CPU and RSS figures come from different runs | refuted: the plan labels each and says rough; fresh-eyes reached the same view |

Codex also marked the npx network claim UNVERIFIABLE: the plan now says it was not measured. Its
other UNVERIFIABLE groups (Codex CLI behaviour, the wrapper's option lists, cost-log figures)
rest on files and commands the seat could not reach; the evidence file quotes the outputs.
