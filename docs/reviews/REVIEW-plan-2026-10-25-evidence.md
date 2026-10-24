# Review trail: plan for `--evidence <file>` (PLAN gate, Normal)

Artifact: `docs/reviews/SKILL-PLAN-review-evidence.md`. Depth Normal: Codex (gpt-6.1-sol) + GLM
5.3 on melious, fresh-eyes (Sonnet) in round 1. No red team: the change touches no box, user
data, login, money, deletion or schema. Gate id 20261024T221701Z-6538.

## Round 1 (uncommitted draft, 2026-10-25)

reviewers: codex OK, melious FAILED ("HTTP 200: Insufficient balance for request. Required: 93,
Available: 0"), ollama-cloud FAILED (quota). Only Codex counted: the second seat is owed.
timings: codex 275s (110,055 tokens).

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F1 | codex | BUG | "the same diff with the evidence appended is refused, as today" is false: `diff_headers.pl` ignores text after the last hunk. | Confirmed by a probe (same `base:` line, exit 0, with and without a four-line appendix). Fixed: Why now says the case-study session used `--base none` because SKILL.md step 2 says so for a diff not made by `git diff`, and that the check would in fact have passed; the base-check test now gives the evidence a `diff --git` record the check refuses, so a leak would fail the run. The parser's leniency is a BUGLOG row (2026-10-25). |
| F2 | codex | RISK | The size test cannot protect the paste cut-off: Codex succeeds and the script exits before it. | Fixed: a second size run with every seat failing checks exit 4 and the "paste prompt is not printed" line. |
| F3 | codex | RISK | Order checks with wording and evidence together cover only codex and ollama; agy could put evidence before the wording paragraph and pass. | Fixed: the three plain-diff runs (default, agy, all failed) use `--evidence --wording-pass`, so every tier shows the wording paragraph before the evidence; Guards narrows the PLAN/VERIFY placement claim to codex and ollama. |
