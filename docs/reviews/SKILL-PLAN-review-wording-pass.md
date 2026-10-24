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
   when the flag is absent), which every tier prompt (tooled, text-only, agy, portable) carries
   before the `--- BEGIN` marker:

   > WORDING PASS. This pass covers prose only: docs, comments, the review record. Report only a
   > statement that contradicts the code or behaviour it describes, the rest of the repository,
   > or another statement in this ${TYPE} (a BUG), or that would mislead a reader about them
   > (a RISK). Do not report style, phrasing or missing requirements. In a diff, a changed line
   > that is not prose (code, config, a command, a fenced snippet, a generated file) is a BUG:
   > this pass cannot cover it.

   Six lines. It names the severities, so a contradiction is not filed as a follow-up by its
   label. PROMPT_CORE is unchanged, so SKILL.md's quoted copy and `check_prompt_sync.sh` (which
   compares only PROMPT_CORE and checks that each tier prompt begins with it) are unaffected.
   PROMPT_WORDING is assigned after TYPE is known and before the tier prompts, and joins the
   `readonly` line. In each tier prompt it sits after PROMPT_CORE and the tier's own text, where
   `${PROMPT_PLAN}${PROMPT_VERIFY}` sits today: `${PROMPT_PLAN}${PROMPT_WORDING}${PROMPT_VERIFY}`.
   Nothing goes before PROMPT_CORE.
2. **Plans and diffs.** Both. Under `--wording-pass` PROMPT_PLAN (the questions on guards a plan
   proposes) is left out: those questions reopen the design, which a wording pass does not.
3. **`--round`.** Refused, exit 2, right after option parsing, before anything is read or sent:
   "a wording pass is not a round (SKILL.md step 6): drop --round". On a gate past round 3, the
   notice printed for a run without `--round` is replaced under the flag by one line, "note:
   wording pass, not a round of gate <id>, which is at round <N>.", on stderr like the notice, so
   the run's output still shows what it was. Without the flag the notice still prints; its last sentence changes from
   "Right for the final full read and the wording pass; a review round is --round <N+1>." to
   "Right for the final full read; a wording pass passes --wording-pass; a review round is
   --round <N+1>."
4. **`--verify`.** Allowed, for the wording pass's confirmation (SKILL.md step 6): the prior-findings
   file holds the contradiction found and its fix, and the delta is the fix. PROMPT_WORDING comes
   before the verification scope. PROMPT_VERIFY is unchanged, including its OUTSIDE SCOPE heading:
   an outside-scope RISK or NIT is a follow-up and an outside-scope BUG is triaged, which matches
   step 6 (a confirmation's other findings are follow-ups; only a substantive BUG reopens the
   rounds). Whether a reviewer reads the round's "new problems" as contradictions only is model
   behaviour, not shown by any test here. A diff still needs `--base`, as every `--verify` diff
   does. Refusing the pair instead would push the confirmation's scope back into the artifact,
   which is the problem this plan fixes.
5. **Only the narrow pass.** The flag is for a seat whose chain is unbroken up to the head the
   delta starts from. Where closeout sends the full pair instead (no unbroken chain), that run is
   a full-scope review without the flag: its diff can hold code gated earlier, which the
   paragraph would wrongly report as a BUG. The same holds when the delta since the last round
   holds a non-prose line (a NIT fixed in code after the last round, say): that whole delta,
   prose included, is re-gated full-scope without the flag, not counted as a round, and that
   re-gate stands in for the wording pass on it. A BUG the seat raises on a non-prose line means this: it is neither fixed
   as a contradiction nor carried as a follow-up, but sends that delta to the full-scope
   re-gate.
6. **`--seat`, `--depth`, `--local-only`.** Unchanged. The skill asks for one cross-model seat;
   running the pair costs more but is not wrong, so the script does not require `--seat`. The
   existing one-reviewer note already names the wording pass. A text-only seat (ollama, melious)
   sees only what it is sent, so it can check the prose against itself and the delta, not against
   the code: the docs recommend `--seat codex`.
7. **Cost log.** Unchanged. A wording pass is logged as a run with no round, as today, and the gate
   line already counts those. A new column would change `review_log.sh` and every reader of an
   append-only file for a label the trail already gives.
8. **Codex effort.** Unchanged: `--verify` still drops to medium, a plain wording pass uses
   config.toml's. Not part of this change.

## Docs

- SKILL.md step 6, the wording pass: run it with `--wording-pass` (its confirmation with
  `--wording-pass --verify`), `--seat codex` preferred for the reason in How 6, and never put the
  scope in the artifact or the `--verify` file. One sentence gives How 5's rule for a non-prose
  line, so a BUG on one has a disposition. Step 2's usage line names the flag.
- `references/closeout.md`, clerk item 2: the narrow prose-only re-gate runs with
  `--wording-pass`, replacing "prepended to the unchanged strict prompt"; the full-pair fallback
  runs without it, and so does a delta holding a non-prose line (How 5). The classification and carry-over go in the trail, not the scope;
  PROMPT_WORDING's last sentence (a non-prose line is a BUG) is what asks the seat to challenge
  it.
- The script's header usage, the `USAGE` string, and a comment above PROMPT_WORDING (two lines).
  The header comments that call the wording pass a run with no `--round` (lines 104, 122, 215)
  stay true and are not changed; the comment at line 295, above the notice, gains a clause
  saying the flag prints the one-line note instead.

## Tests

All in `test_failed_tier_report.sh`, which enters the way users call the script (`bash
independent_review.sh <file> …`) with stub `codex`, `ollama` and `agy` CLIs that record the prompt
they were sent. New case 25c. Its six expected lines are literal in the test (as case 25b holds
`GUARDS=`), never read back from the script, and must appear as one contiguous block in order,
so a cut or scrambled paragraph fails it. Like 25b, it takes
three runs for the plain diff: the default run (codex, ollama), one with `WITH_ANTIGRAVITY=1`
(agy), and one where every seat fails and the run exits 4 (the paste prompt, as in case 5).

- Diff with `--wording-pass`: in the codex, ollama and agy prompts and the paste prompt, every
  line of the paragraph, rendered ("this diff"), comes before `--- BEGIN diff ---`. Checking each
  line, not a marker, catches a paragraph cut short or moved inside the artifact block, which is
  the failure we saw. Melious sends the same PROMPT_TEXTONLY as ollama, so the ollama check
  covers its text.
- Plan with `--wording-pass`: every line of the paragraph, rendered ("this plan"), before
  `--- BEGIN plan ---`; the guards paragraph absent.
- `--wording-pass --verify` on a diff: in the codex and ollama prompts, the order is every
  rendered line of the paragraph ("this diff"), then "VERIFICATION ROUND.", then
  `--- BEGIN PRIOR FINDINGS ---`, then `--- BEGIN diff ---`. The same on a plan ("this plan"),
  with the guards paragraph absent.
- No flag: no "WORDING PASS." in the codex, ollama and paste prompts the existing cases record
  (case 25's `noverify` run, case 5's paste output).
- `--wording-pass --round 2`: exit 2, the message, and no stub ran.

`test_round_checks.sh`: line 127's expected notice takes the new last sentence; a new case on a
logged gate past round 3 runs `--wording-pass` with no `--round` and checks that the one-line
note prints, exactly, with the logged gate's id and round, and the notice does not, beside line 370's case, which still checks the notice without the flag (it matches only
the notice's opening, which does not change).

What the tests cannot show: whether a reviewer honours the scope. That is a live run; the first
wording pass after merge is it, and the trail records whether the seat kept to the scope.

## Guards this adds

- The `--round` refusal catches only a host that passes both flags. A host that runs a wording
  pass without the flag gets today's behaviour.
- The BUG sentence on non-prose lines catches only what the reviewer notices, and a text-only seat
  sees only the delta. The host still decides prose-only from the hunk inventory (closeout); this
  sentence is a second look, not a substitute.
- Case 25c's line-by-line order check fails if, on a plain diff, the codex, ollama, agy or paste
  prompt loses the paragraph, cuts it, or places it after the artifact marker; its plan and
  `--verify` runs check the codex and ollama prompts only. Melious is covered only because it
  sends the same PROMPT_TEXTONLY as ollama; a melious-only change to that path would get past it.
  It says nothing about what a reviewer does with the paragraph.

## Review

Plan: PLAN gate, Normal (Codex + GLM 5.3 on melious), until no BUG is open, then the final full
read. No red team: the change touches no box, user data, login, money, deletion or schema.
Diff: Normal at least (the skill ships in croftweaver.zip), `make check` before each round.
Trail: `docs/reviews/REVIEW-plan-2026-10-24-wording-pass.md`.
