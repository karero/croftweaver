# Review trail: DIFF gate, read-backs as `--evidence` (bc81006c)

Gate: DIFF, depth Normal (`SKILL.md` is an instruction file agents load, so never Light; not High:
no auth, data, secrets or deploy). Plan: `SKILL-PLAN-review-readback-evidence.md`, PLAN gate in
`REVIEW-plan-2026-10-27-readback-evidence.md`. Base 47013aa4 (`--base HEAD~1`, the plan's last
commit). Evidence: the test file's results and the mutation check.

| Round | Artifact | Seats | Findings | Disposition |
|-------|----------|-------|----------|-------------|
| 1 | diff 47013aa4..bc81006c, 2 files, +19/-2 | codex OK (81 s, 40,331 tokens); melious FAILED (balance, "Available: 0"); fresh-eyes Sonnet OK (~87k tokens) | none | clean |

Round 1 counts as codex alone. melious FAILED (balance, "Insufficient balance … Available: 0"), as
in every run of this change's PLAN gate.

UNVERIFIABLE, round 1: codex 2 (the full suite's result has no kept full output; what the review
models do with a READ), fresh-eyes 0. Neither is a finding: `make check` ran in full after the
round, and model behaviour is what the plan's ten-round check measures.

Codex reproduced the mutation check: deleting each sentence fails exactly its own check
(`[1,0,0]`, `[0,1,0]`, `[0,0,1]`).

Cost: codex 40,331 tokens; fresh-eyes ~87k; melious 0.
