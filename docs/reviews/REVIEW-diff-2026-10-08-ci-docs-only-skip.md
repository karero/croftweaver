# REVIEW — DIFF gate, template CI skips docs-only changes, 2026-10-08

**Branch:** `ci/docs-only-skip`, base `origin/main` @ `ae190f7`. Depth: Normal (a CI gate that runs in client repos; no auth, data or deploy path). Produced by the session that opened the PR.
**Reviewers:** Codex (gpt-6.1-sol, read-only) and GLM 5.3 on melious.ai (ollama CLI absent, seat skipped). No fresh-eyes pass was run. Both rounds had two counted reviewers. Data release: owner said yes in chat to Codex + GLM 5.3 on melious.

| Round | Artifact | BUG | RISK | NIT |
|---|---|---|---|---|
| 1 | full diff | 0 | 2 | 2 |
| 2 | fix delta | 1 (disputes round 1's disposition record, not the code) | 2 (re-raised) | 0 |

2 rounds, 7 findings.

## Findings

| # | Sev | Finding | Disposition |
|---|---|---|---|
| 1 | RISK | A failed `changes` job skips `test`, and a skipped job counts as passed. | FIXED: `test.if` is `!cancelled() && (changes.result != 'success' \|\| run == 'true')`. Verified by round 2 across failure, skipped and cancelled. |
| 2 | RISK | Unsupported claim that a job skipped by `if:` satisfies a required check. | REFUTED. GitHub's "Troubleshooting required status checks" says "A job is skipped by a conditional: the job reports Success", and "A job depends on a failed job: the dependent job is skipped and may not block merging" (the case #1 closes). My first round-2 evidence (`template-tests-ok`) was wrong: that job runs and reads upstream results, so it does not exercise a skipped required job. Round 2's BUG is that disposition; the corrected evidence is the docs quote. Not proven on a live ruleset (see below). |
| 3 | RISK | Billing diagnosis ($0 Actions budget blocks private jobs) unsupported. | PARTLY FIXED: the remedy now applies only if the owner wants CI past the free minutes. The diagnosis comes from the reporting session's billing-API check and the owner's Budgets screenshot, not from this review. |
| 4 | NIT | Concurrency comment too long. | FIXED |
| 5 | NIT | File list not logged. | FIXED |

## Not verified

- A docs-only PR against a real ruleset requiring `test` (the "Done when" proof). This repo's CI runs `template-tests.yml`, not the template's `ci.yml`.
- That CI restarts after the Actions budget change.
