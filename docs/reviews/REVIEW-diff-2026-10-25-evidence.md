# Review trail: `--evidence` build (DIFF gate, Normal)

Change: the build of `docs/reviews/SKILL-PLAN-review-evidence.md` on `feat/review-evidence`,
with the owner's go of 2026-10-25 ("Go on the --evidence plan. Merge #405 once CI is green, then
build --evidence as its own PR on top."). Depth Normal (the skill ships in croftweaver.zip):
Codex (gpt-6.1-sol) + GLM 5.3 on melious, fresh-eyes (Sonnet) in round 1. Artifact:
`git diff origin/main...HEAD -- . ':(exclude)docs/reviews/'`.

Before review: `make check` green (after one fix: the END-marker check piped into `grep -q`,
which `check_pipefail_pipes.sh` refuses; it reads a here-string now). The new tests were
mutation-checked in four copies of the scripts, each with one break: agy's prompt without the
block (1 check failed), the text-only prompt with the evidence before the wording paragraph (5),
CONTENT_BYTES without the evidence (5), the END-marker check without trailing blanks (6).

## Round 1 (head acf69418)

reviewers: codex OK, melious OK. timings: codex 395s (103,874 tokens), melious 243s (35,924
tokens); fresh-eyes 445s (143,128 tokens). base: dfcb2bbe (merge base with origin's HEAD
6439b81c, fetched; every changed tracked file present).

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F1 | codex | BUG | SKILL.md step 3 told fresh-eyes to copy the block from `codex.prompt`, but that pass starts before the script writes it, and the file is missing when Codex does not run. | Fixed: the host builds the block from the evidence file and PROMPT_EVIDENCE's lead. Also fresh-eyes' NIT on the same sentence. |
| F2 | codex | BUG | The test comment said "a cut block fails", but only the block's edges were checked; a middle line could go. | Fixed: the whole text between the markers must equal the file as read; a new case cuts a middle line and expects the check to fail. |
| F3 | melious | RISK | BUGLOG's "ignores text after the last hunk" vs T3e's control, where an appended record is refused. | Fixed: the row says non-diff text, and that an appended record is still refused (T3e control). Fresh-eyes reproduced both behaviours on `diff_headers.pl`. |
| F4 | melious | NIT | Only the END marker is refused; a stray BEGIN line would nest. | Refuted: a BEGIN line inside the block cannot move text out of it; END can, which is why the plan refuses it alone. |
| F5 | melious | NIT | `$(cat)` drops NUL bytes, so binary evidence changes silently. | Re-sorted: rare; the artifact and prior findings are read the same way, and evidence is text (output, logs, measurements). |
| F6 | melious | NIT | The second-`--evidence` refusal does not print USAGE like its siblings. | Fixed. |
| F7 | fresh-eyes | NIT | SKILL.md's size sentence did not say the evidence counts, or "trim the evidence". | Fixed. |

Round 2 is earned by F1 (it changes what the host does) and F2 (a guard credited with more than it caught).

## Round 2 (verification, delta acf69418..dcbb46ef)

reviewers: codex OK (effort medium), melious FAILED ("Insufficient balance for request.
Required: 113, Available: 0": out of credit again after round 1), ollama-cloud FAILED (quota).
timings: codex 153s (90,187 tokens). F1–F7 confirmed except below.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F8 | codex | BUG | F2's fix claimed a padded block fails, but `$(...)` drops trailing newlines on both sides, so a blank line before END passed. | Fixed: both sides keep their trailing newlines (a sentinel inside each substitution); new cases: a block padded before END fails, the prompt as sent passes. |

Round 3 is earned by F8 (a guard that could not fire on the input it named).
