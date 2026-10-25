# Review trail: `--wording-pass` build (DIFF gate, Normal)

Change: the build of `docs/reviews/SKILL-PLAN-review-wording-pass.md` (#398) on
`feat/review-wording-pass-build`. Depth Normal (the skill ships in croftweaver.zip): Codex
(gpt-6.1-sol) + GLM 5.3 on melious, fresh-eyes (Sonnet) in round 1. Artifact:
`git diff origin/main...HEAD -- . ':(exclude)docs/reviews/'`. `make check` green before round 1.

Before review, the new tests were mutation-checked by hand, each mutation in the script and
then restored: the paste prompt without the paragraph (caught, 1 check), the paragraph after the
verification scope in the tooled prompt (caught, 2 checks), two of its lines swapped (caught, 10
checks).

## Round 1 (head df6555a4)

reviewers: codex OK, melious FAILED ("HTTP 200: Insufficient balance for request. Required: 93,
Available: 0"), ollama-cloud FAILED (quota). The second seat is owed.
timings: codex 193s (68,443 tokens).
base: 11a13e2d (merge base with origin's HEAD 35bef3fc, fetched; every changed tracked file present)

Codex: No BUG/RISK/NIT findings.

Fresh-eyes (Sonnet): 838s, 132,513 tokens. It ran both test files and mutated a copy (the
paragraph dropped from the agy and paste prompts only): exactly those two checks failed.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F1 | fresh-eyes | NIT | BUGLOG's "Fixed:" text dated the incident 2026-10-24 and put the scope note in the `--verify` file; the repo's record (`REVIEW-plan-2026-10-14-pr303.md:179`) has it heading the artifact. | Fixed: the row cites that record and says both channels are untrusted data. |
| F2 | fresh-eyes | NIT | The comment above PROMPT_PLAN says it is empty for a diff; it is now also empty under `--wording-pass`. | Fixed: comment. |

No BUG or RISK in round 1, so the rounds end. The fixes are prose (a comment and a BUGLOG row):
they go through closeout's prose-only re-gate, run with `--wording-pass` itself.

## Prose-only re-gate (head 43b3dbdd, delta from df6555a4)

Run with the new `--wording-pass --seat codex --base df6555a4`: the flag's first live use.
reviewers: codex OK; timings: codex 81s (36,102 tokens). No BUG/RISK/NIT findings. Codex
checked each prose claim against the code, said the delta was prose only (no executable line),
and raised nothing outside the scope: it kept to the paragraph.

## GLM 5.3 seat (head 4ea6a4af, whole diff, after melious was topped up)

`--seat melious`, MELIOUS_MODEL=glm-5.3, no `--round` (the owed second seat, full scope).
timings: melious 164s (26,341 tokens). base: 11a13e2d (merge base with origin's HEAD 8ec4cb88,
fetched; every changed tracked file present). No BUG.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F3 | melious | RISK | Case 25c's "no stub ran" check fails if the refused run leaves no marks folder. | Refuted: the test's `run` helper creates it first (`mkdir -p "$T/$name.marks"`), and the check passes. |
| F4 | melious | NIT | closeout says the prompt asks for any non-prose changed line as a BUG; PROMPT_WORDING asks that only in a diff. | Fixed: "any changed line of a diff". |
| F5 | melious | NIT | `--wording-pass` without `--seat` runs the pair, which step 6 does not ask for. | Refuted: the reviewed plan (How 6) chose not to require `--seat`; the pair costs more but is not wrong. |

No substantive BUG or earning RISK. The fix is prose: confirmed by the re-gate below.

