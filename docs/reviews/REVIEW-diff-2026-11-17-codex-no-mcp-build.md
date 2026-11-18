# DIFF review — branch `claude/intelligent-lamport-dca91d` — Codex review runs turn off their MCP servers

Plan: `docs/reviews/SKILL-PLAN-review-codex-no-mcp.md`, built as its tasks say. Depth: Normal (it
changes the review script and a Perl helper; no High-row topic). Seats: Codex alone (REVIEW-RULES)
plus the fresh-eyes seat at round 1 (sonnet sub-agent given the diff and the strict prompt).
Gate id `20261117T212808Z-54551`. This session built the change and made every commit.

Checks: `make check` passed before round 1 (after merging `origin/main` with the cut-or-continue
change, no conflicts) and after round 1's fixes. The tests were mutation-checked before round 1
(four mutations; see the PR) and after the fixes (two more, below). The live check is
`evidence-codex-no-mcp/live-check.md`.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|-------|------|----------|-----------|-----------------|--------------|
| 1 | `ad7ef8ab` | the whole PR diff vs `origin/main` | Codex alone; fresh-eyes on `sonnet` | Codex 125 s, 48,640; fresh-eyes 178 s, 115,033 | Codex 1 / 1 / 0; fresh-eyes 0 / 2 / 5 |
| 2 | `dc110eca` | the fixes, `--verify` round 1's findings, `--base ad7ef8ab` | Codex alone (medium) | 134 s, 40,715 | 0 / 1 / 0 (a re-raise) |

Gate total 204,388 tokens, 2 rounds, 9 findings (1 BUG, 3 RISK, 5 NIT) before the re-raise.

## Round 1 findings

| Id | Sev | Source | Finding | Disposition |
|----|-----|--------|---------|-------------|
| A1 | BUG | Codex | three docs said every enabled server is turned off; names that are not plain keys stay on | fixed: setup-guide, rationale, script header say so; confirmed in round 2 |
| A2 | RISK | Codex | the flags are not tested against a real Codex | refuted: CI has no Codex login; the stub test pins the argv, the live check is the proof |
| F1 | RISK | fresh-eyes | no test where `mcp list` exits 0 with an unreadable answer: dropping `|| mcp_why=` survived | fixed: cases `garbage` and `noflag`; mutation (drop it) fails 4 checks; confirmed in round 2 |
| F2 | RISK | fresh-eyes | an entry with no `enabled` key counted as disabled, silently | fixed: helper exits 1, fallback and note; mutation (drop the check) fails 2 checks; confirmed in round 2 |
| N1 | NIT | fresh-eyes | `mcp list` runs before the UTF-8 refusal | re-sorted: rare, up to 20 s on a refused prompt; moving it changes the argv order |
| N2 | NIT | fresh-eyes | first stderr line may be a warning; a perl-less host blames the listing | re-sorted: rare; the fallback and a note still fire |
| N3, N4 | NIT | fresh-eyes | stub comment, "one run each" in the test header | fixed |
| N5 | NIT | fresh-eyes | "above codex_model" against "above codex_bin" | refuted: the note is above `codex_model`; confirmed in round 2 |

## Round 2

Codex confirmed A1, F1, F2, N3, N4, N5 as fixed (it re-ran the helper and the mutations). It
re-raised A2 as RISK: the two live runs had no inspectable record. Disposition: fixed by adding
`evidence-codex-no-mcp/live-check.md` (command, version, the sampled child commands, what was and
was not seen). A docs-only change; no round owed (SKILL.md step 6, stop condition (a2)). N1 and N2
remain re-sorted as rare ("their rarity remains unverified": the re-sort is mine).

Stopped: clean at round 2 apart from the A2 re-raise, closed by the evidence file. "Closing edits
not externally re-verified."
