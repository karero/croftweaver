# Plan: a `--wording-pass` flag for independent-review

Status: plan, not built. Owner go needed before building.

## What

Add `--wording-pass` to `skills/independent-review/scripts/independent_review.sh`. It puts the
narrow scope of the wording pass (SKILL.md step 6) and of the prose-only re-gate
(`references/closeout.md`, clerk item 2) into the script's own prompt, outside the reviewed text.

## Why

The skill tells the host to give the wording pass a narrow scope: flag only a factual
contradiction or a misleading claim, not style. The script has no way to carry that scope. The
host can only put it in the artifact or in the `--verify` file, and both reach the reviewer inside
blocks the prompt calls untrusted data. PROMPT_CORE asks reviewers to report text that tries to
change their task, so a scope note there reads as an attempt to restrict them. On 2026-10-24 Codex
did exactly that: it set the scope note aside as possible steering and reviewed at full scope.
The prompt worked as designed. The scope has to come from the prompt itself.

`closeout.md` already says the scope "is prepended to the unchanged strict prompt"; today nothing
can do that.

## How

1. **Flag.** `--wording-pass` takes no value. It sets a fixed paragraph, PROMPT_WORDING (empty
   without the flag, like PROMPT_PLAN), which every tier prompt (tooled, text-only, agy, portable)
   carries before the `--- BEGIN` marker:

   > WORDING PASS. This ${TYPE} should change only prose: docs, comments, the review record.
   > Report only a statement that contradicts the code or behaviour it describes, the rest of the
   > repository, or another statement in this ${TYPE}, or that would mislead a reader about them.
   > Do not report style, phrasing or missing requirements. In a diff, a changed line that is
   > code, config or a command is a BUG: this pass cannot cover it.

   Five lines. PROMPT_CORE is unchanged, so SKILL.md's quoted copy and `check_prompt_sync.sh` are
   unaffected. PROMPT_WORDING joins the `readonly` line.
2. **Plans and diffs.** Both. Under `--wording-pass` PROMPT_PLAN (the questions on guards a plan
   proposes) is left out: those questions reopen the design, which a wording pass does not.
3. **`--round`.** Refused, exit 2, before anything is read or sent: "a wording pass is not a round
   (SKILL.md step 6): drop --round". The notice that a run without `--round` on a gate past
   round 3 was not counted as a round is not printed for a wording pass: the flag says what the
   run is.
4. **`--verify`.** Allowed, for the wording pass's confirmation (SKILL.md step 6): the prior-findings
   file holds the contradiction found and its fix, and the delta is the fix. PROMPT_WORDING comes
   before the verification scope, so "new problems" in the changed text are read as contradictions
   only. A diff still needs `--base`, as every `--verify` diff does. Refusing the pair instead would
   push the confirmation's scope back into the artifact, which is the problem this plan fixes.
5. **`--seat`, `--depth`, `--local-only`.** Unchanged. The skill asks for one cross-model seat;
   running the pair costs more but is not wrong, so the script does not require `--seat`. The
   existing one-reviewer note already names the wording pass.
6. **Cost log.** Unchanged. A wording pass is logged as a run with no round, as today, and the gate
   line already counts those. A new column would change `review_log.sh` and every reader of an
   append-only file for a label the trail already gives.
7. **Codex effort.** Unchanged: `--verify` still drops to medium, a plain wording pass uses
   config.toml's. Not part of this change.

## Docs

- SKILL.md step 6, the wording pass: run it with `--wording-pass` (its confirmation with
  `--wording-pass --verify`), and never put the scope in the artifact or the `--verify` file.
  Step 2's usage line names the flag.
- `references/closeout.md`, clerk item 2: the prose-only re-gate runs with `--wording-pass`;
  replace "prepended to the unchanged strict prompt" with that.
- The script's header usage, the `USAGE` string, and a comment above PROMPT_WORDING (two lines).

## Tests

All in `test_failed_tier_report.sh`, which enters the way users call the script (`bash
independent_review.sh <file> …`) with stub `codex`, `ollama` and `agy` CLIs that record the prompt
they were sent. New case 25c:

- Diff with `--wording-pass`: the codex, ollama and agy prompts and the paste prompt carry
  "WORDING PASS.", and in each it comes before `--- BEGIN diff ---`. That order is the property
  the change exists for: the same paragraph inside the artifact block is the failure we saw.
- Plan with `--wording-pass`: the paragraph is there, the guards paragraph is not.
- `--wording-pass --verify`: both paragraphs, wording first.
- No flag: no "WORDING PASS." in the prompts the existing cases record.
- `--wording-pass --round 2`: exit 2, the message, and no stub ran.

`test_round_checks.sh`: on a logged gate past round 3, `--wording-pass` with no `--round` prints
no "no --round" notice.

What the tests cannot show: whether a reviewer honours the scope. That is a live run; the first
wording pass after merge is it, and the trail records whether the seat kept to the scope.

## Guards this adds

- The `--round` refusal catches only a host that passes both flags. A host that runs a wording
  pass without the flag gets today's behaviour.
- The BUG sentence on code in a diff catches only what the reviewer notices. The host still decides
  prose-only from the hunk inventory (closeout); this sentence is a second look, not a substitute.

## Review

Plan: PLAN gate, Normal (Codex + GLM 5.3 on melious), until no BUG is open, then the final full
read. No red team: the change touches no box, user data, login, money, deletion or schema.
Diff: Normal at least (the skill ships in croftweaver.zip), `make check` before each round.
