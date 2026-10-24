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
