# Review trail: plan for `--wording-pass` (PLAN gate, Normal)

Artifact: `docs/reviews/SKILL-PLAN-review-wording-pass.md`. Seats: Codex (gpt-6.1-sol) + GLM 5.3
on melious; fresh-eyes (Sonnet) in round 1. Gate id 20261024T151000Z-3153.

## Round 1 (plan at 296a83d0)

timings: codex 403s (101,959 tokens), melious 90s (11,655 tokens), fresh-eyes 131s (131,061 tokens).

Sections changed since round 1: How 1 (paragraph text), How 3, How 4, How 5 (new), How 6,
Docs, Tests, Guards this adds.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F1 | codex | BUG | Closeout's full-pair fallback (no unbroken chain) would also get the flag, and its diff can hold code gated earlier, which the paragraph calls a BUG. | Fixed: new How 5 and the closeout Docs bullet: the fallback runs without the flag. |
| F2 | codex, fresh-eyes | RISK | Paragraph order is credited with making `--verify` report contradictions only; PROMPT_VERIFY still asks for OUTSIDE SCOPE findings. | Fixed: How 4 now says PROMPT_VERIFY is unchanged, that its OUTSIDE SCOPE handling matches step 6's confirmation rule, and that the "contradictions only" reading is untested model behaviour. |
| F3 | codex, melious (NIT) | RISK | The order test checks only the "WORDING PASS." marker: a cut or misplaced paragraph body passes; `${TYPE}` not checked rendered. | Fixed: Tests check every rendered line of the paragraph before the marker (and before the prior-findings block). |
| F4 | fresh-eyes | RISK | Paragraph names no severity; a contradiction labelled RISK becomes a follow-up. | Fixed: How 1 paragraph names BUG for a contradiction, RISK for a misleading claim. |
| F5 | fresh-eyes | RISK | "This ${TYPE} should change only prose" means nothing for a plan. | Fixed: opening is now "This pass covers prose only". Plan test checks the rendered text. |
| F6 | fresh-eyes | RISK | The round-3 notice's text and `test_round_checks.sh` lines 127 and 370 were not in the plan. | Fixed: How 3 gives the new last sentence; Tests list line 127, the new case, and line 370's case unchanged. Header comments 104/122/215/295 checked: still true, unchanged (Docs). |
| F7 | fresh-eyes | RISK | A text-only seat (ollama) cannot check prose against code, yet step 6 allows it. | Fixed: How 6 says so; the SKILL bullet recommends `--seat codex`. |
| F8 | fresh-eyes | RISK (low) | Closeout's "state the classification and carry-over in the scope" has nowhere to go. | Fixed: closeout Docs bullet: classification and carry-over go in the trail; the paragraph's last sentence asks for the challenge. Paragraph now names fenced snippets and generated files. |
| F9 | melious | RISK | Unsupported claim that `check_prompt_sync.sh` compares only PROMPT_CORE. | Refuted: Codex and fresh-eyes both read it (check_prompt_sync.sh:69, `core_of`/`quote_of`): it compares PROMPT_CORE with SKILL.md's quote and checks each tier prompt begins with `${PROMPT_CORE}`. How 1 now states this. |
| F10 | melious | NIT | No-flag test inherits existing tier coverage; paste prompt maybe not checked. | Fixed: Tests name case 5's paste output in the no-flag check. |
| F11 | fresh-eyes | NIT | Melious seat not in case 25c. | Refuted as a gap: melious sends PROMPT_TEXTONLY, the same variable the ollama check reads; Tests say so. |
| F12 | fresh-eyes | NIT | "empty without the flag, like PROMPT_PLAN": PROMPT_PLAN is empty for a diff, not a missing flag. | Fixed: wording. |

Round 2 is earned by F1 (a substantive BUG).

## Round 2 (verification, plan at d340e3b2)

timings: codex 119s (66,290 tokens, effort medium), melious 106s (15,537 tokens). Every round 1
disposition confirmed by both seats.

Sections changed since round 2: How 1 (placement sentence), Tests (`--verify` bullet), Guards
this adds (bullet 3).

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F13 | codex | BUG | The `--verify` test put "VERIFICATION ROUND." after the prior-findings marker; PROMPT_VERIFY puts it before (script:810, 823), so the test would reject a correct build. | Fixed: the bullet now states the order paragraph → "VERIFICATION ROUND." → prior-findings marker → artifact marker. |
| F14 | melious | RISK | F3 half-landed: the `--verify` bullet does not check the rendered `${TYPE}`. | Fixed: the bullet names "this diff" / "this plan". |
| F15 | melious | RISK | Placement relative to PROMPT_CORE unstated; prepending (closeout's old word) would break check_prompt_sync's begins-with check. | Fixed: How 1 gives the exact splice, after PROMPT_CORE, and says nothing goes before it. |
| F16 | melious | RISK | Guard bullet 3 claims "any tier"; melious's prompt is not recorded. | Fixed: narrowed to the four recorded prompts, naming the melious gap. |
| F17 | melious | NIT | Guards-absent not checked under `--verify` on a plan. | Fixed: the `--verify` bullet adds a plan run with the guards paragraph absent. |

Round 3 is earned by F13 (a BUG: the test spec contradicted the code).

## Round 3 (verification, plan at f49ab5a0)

timings: codex 69s (59,786 tokens, effort medium), melious 235s (30,805 tokens). Codex: no
BUG/RISK/NIT findings, every disposition F1-F17 confirmed. Melious: F13-F17 confirmed.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F18 | melious | RISK | Guard bullet 3 credits all four prompts, but the plan and `--verify` runs check codex and ollama only. | Fixed (wording, claim narrowed): bullet 3 says which run checks which prompts. |
| F19 | melious | RISK | Line 370's case may assert the notice's full text and break when its last sentence changes. | Refuted: test_round_checks.sh:370 matches only the opening ("note: no --round, so this run is not a round of gate $id, which is at round 5"), which does not change; Codex read it the same way in round 2. Tests now say so. |
| F20 | melious | NIT (outside scope) | No-flag absence check does not cover agy. | Follow-up, not taken: PROMPT_WORDING is one variable, empty without the flag. |

No substantive BUG and no earning RISK in round 3: the rounds end (SKILL.md step 6). Totals:
3 rounds, 20 findings (2 BUG, 13 RISK, 5 NIT; 2 refuted, 1 follow-up).

## Final full read (whole plan at b8143e96)

Kimi K3 on ollama FAILED: weekly usage limit (429), so no Kimi today. Melious already reviewed this
plan, so it could not take this pass. Taken instead by a stronger host-family pass, Fable 5.1
(367s, 190,515 tokens), which had not seen the plan and did not read this trail.

Sections changed since: How 3, How 5, Docs, Tests (case 25c intro, test_round_checks bullet).

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F21 | fable | RISK | Ordinary use: NITs fixed in code after the last round put non-prose lines in the wording pass's delta; the flag makes that a BUG, and neither step 6 nor the plan says what the host does with it, so a head with unseen code could be stamped. | Fixed: How 5 sends such a delta to a full-scope re-gate without the flag (not a round), and says what the BUG means; Docs add the sentence to SKILL.md step 6 and closeout. Earning RISK (changes what the host does): earns round 4, kind `nonprose-disposition`. |
| F22 | fable | NIT | Suppressing the notice leaves no trace that a run on a gate past round 3 was a wording pass. | Fixed: How 3 prints a one-line note instead; test_round_checks bullet checks it. |
| F23 | fable | NIT | How 3 quoted the new notice sentence as a fragment; line 127 needs the exact string. | Fixed: both sentences quoted whole. |
| F24 | fable | NIT | Case 25c needs three runs (agy only with WITH_ANTIGRAVITY=1, paste only when all seats fail). | Fixed: Tests say so, as in case 25b. |
| F25 | fable | NIT | The cut-paragraph claim holds only if the test holds the lines literally. | Fixed: Tests say the six lines are literal. |
| F26 | fable | NIT | Comment at script line 295 would describe pre-change code. | Fixed: Docs add a clause there. |

## Round 4 (verification, plan at 0fd0bddd, `--earned-by nonprose-disposition`)

timings: codex 115s (63,550 tokens, effort medium), melious 200s (30,132 tokens). Codex: no
BUG/RISK/NIT findings, F1-F26 confirmed. Melious: F21-F26 confirmed; NITs only.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F27 | melious | NIT | The new test_round_checks case checks the note's presence, not its text. | Fixed: exact string, with the logged gate's id and round. |
| F28 | melious | NIT | Per-line checks pass a scrambled paragraph; "order" overstated. | Fixed: the six lines must appear as one contiguous block, in order. |
| F29 | melious | NIT | How 5: does the full-scope re-gate cover the prose too, or does a wording pass still follow? | Fixed: the re-gate covers the whole delta, prose included, and stands in for the wording pass on it. |
| F30 | melious | NIT (outside scope) | "the paragraph's last sentence" has an unclear referent. | Fixed: names PROMPT_WORDING's last sentence. |
| — | melious | UNVERIFIABLE | Which stream the note goes to. | Checked: the notice prints to stderr (script line 298, `>&2`); How 3 now says the note does too. |

No BUG and no earning RISK in round 4: the rounds end; NITs fixed without another round (step 6
(a2)). Next: the wording pass over the delta since round 4.
