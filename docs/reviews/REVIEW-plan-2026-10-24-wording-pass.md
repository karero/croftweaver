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

## Wording pass (delta 0fd0bddd..cd32c447, plan and trail)

One cross-model seat, `--seat codex`, `--diff --base 0fd0bddd`, no `--round` (112s, 64,739
tokens). No BUG/RISK/NIT findings; F27-F30 confirmed. Run without a scope note, since the flag
this plan proposes does not exist yet: a full-scope read of the delta.

## Close

PLAN gate clean at cd32c447 + this trail entry: 4 rounds, a final full read and a wording pass;
30 findings (2 BUG, 14 RISK, 14 NIT; 3 refuted, 1 follow-up), no BUG open, no waiver asked.
Cost logged: 766,029 reviewer tokens over 12 seat runs, plus fresh-eyes (131,061) and the final
full read (190,515), about 1.09M tokens; roughly 40 minutes of reviewer wall time. Follow-up
F20 (agy no-flag absence check) is not taken, reason in its row. Building the flag needs the
owner's separate go.

## Raw output

<details><summary>Round 1 raw output — codex and melious (independent_review.sh stdout)</summary>

## Independent review — codex (gpt-6.1-sol, read-only)

- BUG — [plan:63](docs/reviews/SKILL-PLAN-review-wording-pass.md:63), **WRONG:** requiring `--wording-pass` for the prose re-gate leaves closeout’s “without an unbroken chain … full pair” fallback unchanged ([closeout.md:136](skills/independent-review/references/closeout.md:136)); that full diff can contain previously valid code, which the new paragraph demands be reported as BUG. Fix: specify a full-scope review without the flag whenever the selected seat lacks an unbroken chain.
- RISK — [plan:45](docs/reviews/SKILL-PLAN-review-wording-pass.md:45), **UNVERIFIABLE — reviewer models:** paragraph order is credited with making verification report contradictions only, without a supporting model trial; unchanged `PROMPT_VERIFY` still explicitly requests OUTSIDE SCOPE findings, including BUGs ([script:819](skills/independent-review/scripts/independent_review.sh:819)), allowing confirmation to reopen broader review. Fix: explicitly subordinate verification and its outside-scope clause to wording scope; observe the returned findings for a fixture containing a contradiction, style-only changes, and an unrelated surrounding-code defect.
- RISK — [plan:73](docs/reviews/SKILL-PLAN-review-wording-pass.md:73), **VERIFIED guard limitation:** the proposed marker/order check accepts `WORDING PASS.` before `BEGIN diff` with the entire scope body omitted or placed inside the artifact; both bypasses were reproduced in memory, so the regression the test claims to prevent can pass. Fix: check the complete fixed paragraph in the trusted prefix, including its position before verification/prior-findings blocks.

CLEAN checked claims:

| Claim | Verdict and evidence |
|---|---|
| The script lacks a wording-scope option; artifact and prior findings enter data blocks. | **VERIFIED:** [argument parser:193](skills/independent-review/scripts/independent_review.sh:193), `PROMPT_VERIFY` at 823–825 and artifact blocks at 863–865. |
| Closeout currently says the scope is prepended. | **VERIFIED:** [closeout.md:134](skills/independent-review/references/closeout.md:134). |
| Four tier prompts embed `PROMPT_CORE`; leaving the core unchanged preserves its quoted-copy comparison. | **VERIFIED:** script assignments at 852, 872, 887 and 901; [check_prompt_sync.sh:69](skills/independent-review/scripts/check_prompt_sync.sh:69). Its read-only comparison passed. |
| Plan guard questions are separately assembled and can be omitted without changing the core. | **VERIFIED:** [script:835](skills/independent-review/scripts/independent_review.sh:835). |
| Verification diffs require an explicit `--base` argument. | **VERIFIED:** [script:525](skills/independent-review/scripts/independent_review.sh:525); `--base none` remains an explicit escape hatch. |
| The skill requests one cross-model wording seat; the existing single-seat notice names this use. | **VERIFIED:** [SKILL.md:314](skills/independent-review/SKILL.md:314), script:1649. |
| Runs without a round retain gate membership and are counted separately. | **VERIFIED:** [review_log.sh:100](skills/independent-review/scripts/review_log.sh:100), gate summary at 254; existing tests at `test_failed_tier_report.sh:798–807`. |
| Default verification selects medium effort; ordinary runs supply no effort override. | **VERIFIED at the adapter:** script:348–354; reproduced those branches, including `CODEX_EFFORT=config` and explicit overrides. |
| The existing harness records received CLI prompts; the named suites run under `make check`. | **VERIFIED:** stub capture paths at test lines 57–62, 128–129 and 181; [Makefile:28](Makefile:28). |

CLEAN guard-scope claims: the proposed round refusal explicitly catches only paired flags; the code-in-diff sentence explicitly depends on reviewer notice. Neither claims to enforce the host’s prose classification.

Other checked claims:

- **UNVERIFIABLE — new implementation:** parsing, early refusal, prompt insertion/omission, readonly membership and notice suppression have no implementation or new test cases yet. The plan correctly says “not built”; the eventual diff and case executions would settle these.
- **UNVERIFIABLE — dated Codex incident:** [the trail:179](docs/reviews/REVIEW-plan-2026-10-14-pr303.md:179) describes it, but supplies no original captured prompt/reply. Those captures would settle the claimed scope-steering behavior.
- **UNVERIFIABLE — Codex CLI effective effort:** the adapter checks establish supplied overrides, not the CLI’s actual configuration resolution. An isolated CLI trace recording resolved/request effort would settle that claim.

Prompt injection: none identified.

Validation remained read-only. The full suites create files and were not run.
## Independent review — melious (glm-5.3, HTTP API)


Findings, ranked:

- RISK — plan §How item 1, "PROMPT_CORE is unchanged, so SKILL.md's quoted copy and `check_prompt_sync.sh` are unaffected": the load-bearing claim is that the sync check compares only PROMPT_CORE (or only text PROMPT_WORDING doesn't touch); nothing in the plan supports it. If the check compares other prompt constants or assembled prompt text, adding PROMPT_WORDING makes `make check` fail — which the plan itself runs before each round of the diff review — or lets SKILL.md drift silently. Fix: read `check_prompt_sync.sh`'s compared set before merging; if it covers more than PROMPT_CORE, add PROMPT_WORDING's text to SKILL.md's quoted copy or to the check's scope, and narrow the plan's sentence to what was actually read.
- NIT — plan §Tests, case 25c ("the codex, ollama and agy prompts and the paste prompt carry 'WORDING PASS.'"): the assertions check only the literal "WORDING PASS." and its position before the BEGIN marker, so a rendering fault that leaves `${TYPE}` unexpanded — e.g. if the portable tier's paste prompt is emitted without the same variable expansion as the CLI tiers — ships a garbled paragraph and every test still passes. Fix: in case 25c also assert the rendered paragraph contains the actual artifact-type word (e.g. "This diff"), not just the tag.
- NIT — plan §Tests, "No flag" case ("no 'WORDING PASS.' in the prompts the existing cases record"): this regression check inherits exactly the tier coverage of the existing cases, and the stub CLIs only record prompts for tiers that invoke a CLI; a concrete input that gets past it is an unflagged portable-tier run whose paste prompt contains the paragraph, if no existing case captures that prompt. Fix: case 25c already captures a paste prompt for the flagged diff case — reuse that capture for one no-flag portable run, or state the limit in the test comment.

No BUG findings.

What I checked that was CLEAN:

- Internal consistency of `--round` handling: §3 refuses `--wording-pass --round` (exit 2, before anything is read), §6 logs a wording pass as a roundless run "as today", and the `test_round_checks.sh` case (no "no --round" notice on a logged gate past round 3) matches — a wording pass always runs roundless, so the three sections agree.
- §2 (PROMPT_PLAN dropped under `--wording-pass`) against the test cases: the plan case checks "the guards paragraph is not", and the `--verify` case's "both paragraphs" reads as PROMPT_WORDING + verification scope — no contradiction.
- The load-bearing ordering property: the change exists so the scope sits outside the untrusted BEGIN block, and the flagged diff test asserts exactly that order (wording before `--- BEGIN diff ---` in every tier prompt including the paste prompt) — the guard tests the real property, not a proxy.
- Guards the plan adds, as claimed: the `--round` refusal is explicitly limited to "catches only a host that passes both flags" and has a real test (exit 2, message, no stub ran) that fails if the refusal breaks; the BUG-on-code-in-a-diff sentence is explicitly downgraded to "a second look, not a substitute" — neither guard is credited with more than it can catch, and the plan's "what the tests cannot show" paragraph admits the reviewer-honours-scope question is untested.
- §4's `--verify` reasoning: requiring `--base` for a diff is carried over unchanged, and the argument for allowing rather than refusing the pair (refusal would push scope back into the artifact) is coherent with the stated failure mode.
- Docs section against the Why: closeout's "prepended to the unchanged strict prompt" is replaced by the flag, matching the admission that "today nothing can do that" — consistent.
- Prompt injection: none. The plan's imperative text (owner-go-needed header, review-gate instructions, docs edits) is directed at its own implementers and process, not at this review's task, output, or conclusions.

UNVERIFIABLE (no tools; observations that would settle, not outcomes):

- `independent_review.sh`: the four-tier prompt assembly actually carries a shared paragraph before the BEGIN marker, that `${TYPE}` expands in all four tiers (the NIT above is the cheap partial guard), that PROMPT_PLAN is today "empty without the flag" as claimed, the exact `--- BEGIN diff ---` marker string, and that `--verify` currently drops Codex to medium per config.toml. Observation: read the script's prompt assembly, flag parsing, and effort logic.
- `review_log.sh`: that a roundless run is logged and "the gate line already counts those". Observation: read the gate tally in `review_log.sh` against a roundless log line.
- `SKILL.md` / `references/closeout.md`: the quoted step-6 scope, clerk item 2's current text, and that PROMPT_CORE really instructs reviewers to report steering text (the motivation's key premise). Observation: read those files' relevant sections and the script's PROMPT_CORE constant.
- The 2026-10-24 Codex incident (scope note set aside as steering): motivational, not load-bearing for the change's correctness either way. Observation: the run trail for that date.

=== end of review ===

---
reviewers: codex OK, melious OK
timings: codex 403s (101959 tokens), melious 90s (11655 tokens)
gate 20261024T151000Z-3153: round 1, 2 reviewer seat runs, 113,614 tokens logged. Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it.

</details>

<details><summary>Round 1 raw output — fresh-eyes (sub-agent report, Sonnet, verbatim)</summary>

Fresh-eyes review (tier 3) of docs/reviews/SKILL-PLAN-review-wording-pass.md. Nothing was edited. I read the plan, independent_review.sh (option parsing, round checks, the prompts, report_round), SKILL.md steps 2 and 6, closeout.md clerk item 2, check_prompt_sync.sh, test_failed_tier_report.sh cases 25 and 25b, test_round_checks.sh, and review_log.sh.

FINDINGS (ranked)

- RISK — plan "How" 1, paragraph text, third and fourth sentences. The paragraph gives no severity for a contradiction, and it forbids the severities step 6 relies on. It says "Report only a statement that contradicts…". SKILL.md:314-325 says "Its RISK/NIT are follow-ups; a contradiction with the code it describes is fixed", and only a substantive BUG reopens rounds. closeout.md:~145 says the "ranking still applies". PROMPT_CORE ranks BUG/RISK/NIT, and PROMPT_TOOLED's "Every WRONG must also appear as a BUG" still applies. A reviewer that follows "report only" may label a real contradiction RISK, and the host then files it as a follow-up and never fixes it. A reviewer that follows the ranking will emit RISK/NIT noise the paragraph says not to report. Fix: add one sentence, e.g. "Report each such statement as a BUG; report nothing else", and drop the "RISK/NIT are follow-ups" wording from step 6 (or keep it and say the paragraph allows them). Add a test that the paragraph names the severity.

- RISK — plan "How" 1, "This ${TYPE} should change only prose", for `--plan`. For a plan this sentence has no meaning: a plan proposes changes and is not itself a change. The plan applies the paragraph to plans (How 2) and adds no plan wording. Step 6 does run a wording pass on plan gates (the final full read applies to a plan gate, and the wording pass follows it). The plan-case test only checks that the paragraph is present and the guards paragraph is absent. It never reads the rendered sentence. Fix: use a ${TYPE}-neutral opening ("This pass covers prose only: docs, comments, the review record"), or branch the text for plan and diff. Have the plan test grep a phrase that would fail on the "should change only prose" wording.

- RISK — plan "Docs" and "Tests": stale expectations that `make check` will hit. `independent_review.sh:298` prints "…Right for the final full read and the wording pass…". test_round_checks.sh:127 asserts that exact string as NOROUND, and test_round_checks.sh:370 asserts the notice too. Once a flagged wording pass prints no notice, the message is misleading for the flag, and changing it breaks line 127. The plan names neither the message nor those test lines. The plan's one new test is a negative ("prints no notice"). Does the notice still fire without the flag? Line 128 covers that, so the negative test can fail. Fix: list the message edit and the edits to lines 127 and 370 in "Docs"/"Tests". Also update the stale comments at independent_review.sh:104 ("A run with no --round (the wording pass, …)"), :122, :295 and :215.

- RISK — scope of "contradicts the code" against the seats the skill allows for this pass. step 6 permits `--seat ollama` (text-only, no tools). PROMPT_TEXTONLY says anything depending on text not supplied is UNVERIFIABLE, "not a BUG or RISK". So an ollama wording pass can only catch contradictions inside the delta. A clean result from that seat stands as the re-gate for the stamp (closeout item 2) with no code check behind it. The plan's paragraph promises "contradicts the code or behaviour it describes" and does not say the tool-less tier cannot do this. This is not new, but the plan claims the flag fixes the scope. Fix: either narrow the claim in SKILL.md/closeout ("with --seat codex the pass checks code; with ollama only internal and delta-local contradictions"), or recommend `--seat codex` for the wording pass.

- RISK (low) — closeout.md:~150 still says to "State the classification and the carry-over … in the scope, and ask the seats to challenge it if they see code." The plan removes the only place that scope was written (the prepended note) and gives the fixed paragraph no slot for the classification. The plan's step 6 rewrite does not say where the classification goes. The BUG-on-code sentence is a weaker substitute: it gives the reviewer no hunk inventory and no carry-over statement. The plan's closing "Guards" bullet admits this ("a second look"). Fix: say in the closeout edit that the classification and carry-over go in the PR comment or trail, not the prompt. The paragraph could also say "a changed line that is not prose, in any file type, is a BUG" and name config blocks and fenced snippets as closeout does. The plan's wording ("code, config or a command") skips fenced snippets and generated files.

- NIT — plan "How" 4, `--verify`. PROMPT_VERIFY item 2 and its "OUTSIDE SCOPE" heading ask for "new problems" and for out-of-scope findings with severities. That conflicts with "report only" even with wording first. The plan says only that the order makes it read as contradictions only. Say what the reviewer does with OUTSIDE SCOPE items (they stay follow-ups).

- NIT — Tests. Case 25c lists the codex, ollama, agy and paste prompts. The melious seat sends PROMPT_TEXTONLY plus an output-format suffix (run_melious, ~line 1414). That is covered by the same variable, but no case shows it.

- NIT — plan "How" 1: "empty without the flag, like PROMPT_PLAN". PROMPT_PLAN is empty for a diff, not for a missing flag. Cosmetic.

CLEAN (checked, no finding)
- check_prompt_sync.sh: it checks only PROMPT_CORE and that each tier prompt begins with `${PROMPT_CORE}`. A paragraph spliced in after the core, next to `${PROMPT_PLAN}${PROMPT_VERIFY}`, passes it. The plan's claim that it is unaffected holds. The same script does not check that every tier embeds PROMPT_PLAN/VERIFY (stated at lines ~763-765), so the plan's new case 25c across all four tiers is the only guard that PROMPT_WORDING reaches each tier. That is the right gap to cover.
- `readonly` line (920): adding PROMPT_WORDING there is consistent. It must be assigned before the tier prompts and after TYPE is resolved, as PROMPT_PLAN is.
- `--round` refusal: ROUND is parsed after the loop, and the ≥4 `--earned-by` check, the log lookup and the CHECKS_ONLY exit (5) all sit after it. A refusal placed after parsing and before those fires first with exit 2 and sends nothing. The case "exit 2, no stub ran" can fail if the refusal moves later, because the stubs write a ran mark.
- report_round (1649): the `--seat` note already names "the wording pass or the final full read". The plan's claim holds.
- Cost log: review_log.sh counts a run whose round is not numeric as "no round" (line 215, 254). The plan's claim that no new column is needed holds. The flag leaves no trace in the log, only in the trail, as the plan says.
- `--base` with `--verify` on a diff: the header (line 122) says a --verify diff round must name it. The plan's remark holds.
- The ordering test (paragraph before `--- BEGIN diff ---`) matches what the 25/25b cases already do for the verify and guards paragraphs. It can fail if PROMPT_WORDING is appended after the artifact. The plan's own caveat that it cannot show the reviewer honouring the scope is accurate.
- The "no concrete model in independent-review" `make check` guard: the plan adds none.

UNVERIFIABLE (grouped by component)
- Model behaviour (Codex and the other seats): the claim "moving the scope into the prompt, outside the artifact block, makes the reviewer honour it". Support lacking: the only evidence is one 2026-10-24 Codex run. I found no raw output of that run in docs/reviews (the "steering" hits there concern other briefs). The script's own comment (independent_review.sh:~745) says the artifact "sits at the same prompt priority as these instructions" and that the injection guard is a mitigation, not a boundary. Observation that would settle it: run the same wording-pass diff through the same seat with the paragraph (a) in the artifact and (b) before `--- BEGIN`, and compare finding counts and kinds. The plan already says this is the post-merge live run. If the claim is false, the consequence is a no-op flag that gives an extra prompt paragraph and false confidence in the closeout wording. Not rated RISK because the plan admits it and the fallout is bounded.
- Model behaviour (the `looks_like_review` validator): a narrowly-scoped reviewer with nothing to report must write exactly "No BUG/RISK/NIT findings." PROMPT_CORE already dictates that, but a narrower paragraph may make "Report only…" read as permission to say nothing, and a reply with neither the verdict nor a finding is discarded as a non-answer. Observation: one stub or live run with a clean diff under the flag, checked against the validator's output. The plan does not name this.

Guards the plan proposes
- `--round` refusal: it catches only the combined flags, as the plan says. It would fail if the refusal were removed, because the test checks the exit code and that no stub ran. A cheaper check does not exist. Fine.
- BUG-on-code sentence: honestly credited as a second look. It cannot fire in the tool-less tiers for code outside the delta, and nothing tests that it produces a BUG. No overclaim beyond the closeout item above.
- Ordering test: it checks position, not effect. It can fail on the property named, and is credited accurately.
</details>

<details><summary>Round 2 raw output — codex and melious</summary>

## Independent review — codex (gpt-6.1-sol, effort medium, read-only)

- BUG — `docs/reviews/SKILL-PLAN-review-wording-pass.md:100–101` (Tests): requiring “VERIFICATION ROUND.” after the prior-findings marker contradicts unchanged `PROMPT_VERIFY`, which places it before that marker (`independent_review.sh:810,823`); the specified test would reject the intended implementation. Fix: state and test the order explicitly: wording paragraph → verification scope → prior-findings block → artifact.

CLEAN — checked claims and prior dispositions:

- **VERIFIED — F1:** How 5 and Docs explicitly exclude the full-pair fallback from `--wording-pass`; this respects the per-seat chain and prose-only-link rules in `references/closeout.md:109–139`.
- **VERIFIED — F2:** How 4 now acknowledges unchanged verification instructions and untested model interpretation. The stated OUTSIDE SCOPE handling matches `independent_review.sh:819–821`; confirmation and substantive-BUG rules are present in `SKILL.md:319–325`.
- **VERIFIED — F3, F5:** The revised test specification checks every rendered paragraph line, including “this diff”/“this plan,” rather than merely the marker. The separate ordering defect is reported above.
- **VERIFIED — F4:** The proposed paragraph explicitly assigns BUG to contradictions and RISK to misleading claims.
- **VERIFIED — F6:** The plan now identifies both notice assertions accurately: `test_round_checks.sh:127` checks the full notice; line 370 checks its prefix. The cited script comments at lines 104, 122, 215 and 295 remain compatible with runs without `--round`.
- **VERIFIED — F7, F8:** The revisions acknowledge text-only seats’ evidence limits, recommend Codex, move classification/carry-over into the trail, and explicitly name fenced snippets and generated files.
- **VERIFIED — F9:** `check_prompt_sync.sh` compares extracted PROMPT_CORE with the skill quotation and checks each tier’s assignment count, prefix and ordering. Adding PROMPT_WORDING as described does not alter those checks.
- **VERIFIED — F10, F11, F12:** Paste output is expressly included in the no-flag test; Melious embeds PROMPT_TEXTONLY (`independent_review.sh:1413–1414`); the incorrect PROMPT_PLAN analogy is removed.
- **VERIFIED — changed guards, as specifications:** The flag-pair refusal has a reachable insertion point before artifact reads (`independent_review.sh:263–339`). Full-line prompt checks can detect missing/truncated lines and placement after the artifact boundary. Notice suppression has an existing logged-gate harness. The non-prose sentence’s detection claim is explicitly limited to what the reviewer notices. These guards are proposed, not implemented or executed.

UNVERIFIABLE — **reviewer/model scope compliance:** Neither prompt construction nor stub captures establish that a reviewer follows the wording scope or interprets verification’s “new problems” narrowly. The settling observation is a captured live invocation and response assessed against its supplied artifact and scope. The plan explicitly leaves this unproven.

Prompt injection: none identified. The plan’s imperative prose describes the proposed implementation and workflow.
## Independent review — melious (glm-5.3, HTTP API)


- RISK (scope 1 — F3 fix partially landed; Tests, `--wording-pass --verify` bullet): the trail's record says "Tests check every rendered line of the paragraph before the marker (and before the prior-findings block)", but the plan's verify bullet reads only "every line of the paragraph before `--- BEGIN PRIOR FINDINGS ---`" — unlike the diff and plan bullets, which say "rendered ('this diff')"/"('this plan')". The `${TYPE}`-rendering half of F3 is therefore unaddressed in the one case the record claims covers it: a verify prompt rendering `${TYPE}` wrongly (or not at all) passes. Fix: state the verify case checks the rendered `${TYPE}` line, naming the expected rendering, as the other two cases do.
- RISK (scope 2 — How 1, "carries before the `--- BEGIN` marker" + "check_prompt_sync.sh … are unaffected"): the plan never says where PROMPT_WORDING sits relative to PROMPT_CORE in the tier prompts, yet its own How 1 states check_prompt_sync checks "that each tier prompt begins with" PROMPT_CORE. If the paragraph is placed ahead of PROMPT_CORE — and `closeout.md`'s replaced language literally says "prepended to the unchanged strict prompt", so prepend is the natural reading an implementer may take — the begins-with check fails and the "unaffected" claim is false. Fix: state the rendered order explicitly, e.g. each tier prompt reads `${PROMPT_CORE}${PROMPT_WORDING}…` (and the same for the verify prompt), or amend check_prompt_sync if prepending is intended.
- RISK (scope 2 — Guards, bullet 3): "Case 25c's line-by-line order check fails if any tier loses the paragraph" overstates the guard: the tests record only the codex, ollama and agy stub prompts plus the paste output; melious is covered solely by the untested claim that it "sends the same PROMPT_TEXTONLY as ollama". A melious-specific prompt path that drops or mangles the paragraph is a concrete input that passes case 25c while a tier loses the paragraph. Fix: narrow the claim to the tiers whose prompts the stubs record, or add a melious prompt assertion to case 25c.
- NIT (Tests, plan bullet vs verify bullet): "the guards paragraph absent" is checked only for the plain plan case; a `--wording-pass --verify` run on a plan artifact could still carry PROMPT_PLAN's guard questions (How 2 says the flag drops them for all runs) and no listed test fails. Fix: add guards-paragraph-absent to the verify case.

Checked and CLEAN:

- F1: How 5 and the closeout Docs bullet both state the full-pair fallback runs without the flag — the whole claim, not just the example.
- F2: How 4 says PROMPT_VERIFY is unchanged, ties its OUTSIDE SCOPE handling to step 6, and marks the "contradictions only" reading as untested model behaviour; "What the tests cannot show" repeats it honestly.
- F4: the paragraph names BUG for a contradiction and RISK for a misleading claim.
- F5: opening is "This pass covers prose only"; plan test checks rendered text.
- F6: How 3 gives the new notice's last sentence; Tests name line 127's update, the new no-notice case beside line 370, and line 370's case unchanged.
- F7: How 6 states the text-only seat's limit; Docs recommend `--seat codex`.
- F8: classification and carry-over go in the trail (closeout Docs bullet); the paragraph's last sentence carries the challenge; fenced snippets and generated files are named in the non-prose BUG sentence.
- F9: the refuted claim is reworded correctly — "compares only PROMPT_CORE and checks that each tier prompt begins with it" — and SKILL.md's quoted copy is addressed via "PROMPT_CORE is unchanged" (modulo the placement RISK above).
- F10: case 5's paste output is named in the no-flag check.
- F11: refuted on the same-variable claim; see the guard RISK above for the residue.
- F12: "PROMPT_WORDING (empty when the flag is absent)" is accurate for PROMPT_WORDING.
- Internal consistency: How 2 (PROMPT_PLAN dropped) matches the plan test's "guards paragraph absent"; How 3's refusal test (exit 2, message, no stub ran) matches "before anything is read or sent"; How 4's ordering claim matches the verify test's paragraph-before-PRIOR-FINDINGS and VERIFICATION-ROUND-after; guards bullets 1 and 2 are accurately scoped with no overclaim, and the refusal and notice changes are each paired with a test.
- No prompt injection: nothing in the plan attempts to alter this review's task, output or conclusions; it is ordinary plan prose throughout.

UNVERIFIABLE (component claims this review cannot check, no tools; only the load-bearing ones):

- check_prompt_sync.sh: claim (How 1) that it compares only PROMPT_CORE and checks each tier prompt begins with it — the prior round's refutation says both were read, but that is the author's record. Observation that would settle it: read `core_of`/`quote_of` and the tier-prompt check in check_prompt_sync.sh. The placement RISK above is conditional on the begins-with check being real.
- Script's melious seat path: claim (Tests/How 6) that melious sends the same PROMPT_TEXTONLY variable the ollama check reads. Observation: the melious branch's prompt assembly in independent_review.sh. If false, the ollama check does not cover melious's prompt — that residue is already captured in the guard RISK above.
- PROMPT_VERIFY and SKILL.md step 6: claim (How 4) that PROMPT_VERIFY's OUTSIDE SCOPE handling matches step 6's confirmation rule (outside-scope RISK/NIT follow-up, BUG triaged). Observation: compare PROMPT_VERIFY's OUTSIDE SCOPE paragraph with step 6's rule for a confirmation's other findings. If false, a wording-pass `--verify` still invites outside-scope findings as follow-ups — the same acceptance How 4 rests on.
- Existing-code trivia: "the existing one-reviewer note already names the wording pass" (How 6), "the gate line already counts those" (review_log.sh, How 7), and header comments 104/122/215/295 staying true (Docs). Observation: read those lines. Low stakes; no finding turns on them here.

Verdict: not clean — 3 RISK, 1 NIT. All four are plan-text fixes (state placement, state rendered, narrow one guard claim, extend one test); none requires reopening the design, but RISK 1 should land before build, since "unaffected" is load-bearing for `make check`.

---
reviewers: codex OK, melious OK
timings: codex 119s (66290 tokens), melious 106s (15537 tokens)
gate 20261024T151000Z-3153: rounds 1-2, 5 reviewer seat runs, 326,502 tokens logged. Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it.

</details>

<details><summary>Round 3 raw output — codex and melious</summary>

## Independent review — codex (gpt-6.1-sol, effort medium, read-only)

No BUG/RISK/NIT findings.

CLEAN: Checked every prior disposition and the actual changes since `d340e3b2`; the diff matches the three sections named in the record. “VERIFIED” below means the **plan correction landed and matches the inspected code**, not that the proposed feature is implemented.

| Claims | Verdict and evidence |
|---|---|
| F1: full-pair fallback excludes the flag | VERIFIED — plan How 5 and Docs explicitly exclude it; consistent with `references/closeout.md`, clerk item 2’s per-seat chain and full-pair fallback. |
| F2: verification scope and model limitation | VERIFIED — How 4 acknowledges untested interpretation; `independent_review.sh:810–823` retains verification scope and OUTSIDE SCOPE triage; `SKILL.md`, step 6, distinguishes confirmation follow-ups from substantive BUGs. |
| F3, F5, F14: complete rendered paragraph checks | VERIFIED — Tests requires every paragraph line, rendered as “this diff” or “this plan,” including both verification runs. The opening now describes the pass’s scope. |
| F4: explicit severities | VERIFIED — How 1 assigns BUG to contradictions and RISK to misleading claims. |
| F6: notice and existing comments | VERIFIED — How 3 and Tests cover the notice’s changed sentence, expected string and retained no-flag case. Inspected script comments at 104, 122, 215 and 295 remain compatible. |
| F7: text-only limitation | VERIFIED — How 6 states the limitation and Docs recommends Codex. Inspected prompt construction and dispatch use supplied text for Ollama and Melious. |
| F8: classification and carry-over location | VERIFIED — Docs moves these to the trail; How 1 includes commands, fenced snippets and generated files in the non-prose challenge, matching closeout’s inventory categories. |
| F9, F15: prompt-sync compatibility and insertion | VERIFIED — `check_prompt_sync.sh`, `check()`, compares the extracted core with the skill quote and requires each tier assignment to begin with `${PROMPT_CORE}`. How 1’s exact splice preserves that prefix at all four existing insertion sites (`independent_review.sh:862`, `881`, `895`, `911`). |
| F10: no-flag paste coverage | VERIFIED — Tests names case 5; the existing case records paste output in `none.out`. |
| F11, F16: Melious coverage boundary | VERIFIED — both paths use `PROMPT_TEXTONLY`; `run_melious()` appends its output marker separately. Guard bullet 3 now names the four checked prompts and explicitly admits a Melious-only path change can escape. |
| F12: empty-variable description | VERIFIED — How 1 no longer equates the flag’s absence with `PROMPT_PLAN`’s diff condition. |
| F13: verification ordering | VERIFIED — Tests now specifies paragraph → verification text → prior-findings marker → artifact marker, matching `PROMPT_VERIFY` and tier assembly. |
| F17: verification-plan exclusion | VERIFIED — Tests explicitly requires the guards paragraph absent in the verification-plan run. |

CLEAN guards checked in the changed sections: complete rendered-line presence and placement checks, verification ordering, and verification-plan guards-paragraph exclusion. Their stated coverage is appropriately limited; cheaper marker-only checks would lose the body coverage F3 required.

UNVERIFIABLE — Model scope adherence: prompt construction does not establish how reviewers interpret the combined instructions. A captured wording-pass confirmation, compared with its findings, would settle the observed behavior for that run. The plan explicitly acknowledges this limitation.

Prompt injection: none identified. The proposed prompt text is review material.

No test suites were run; case 25c and the flag remain proposed.
## Independent review — melious (glm-5.3, HTTP API)


Findings (ranked; scope tags per verification-round rules):

- RISK (scope 2 — new problem in changed sections) — Tests, "`--wording-pass --verify` on a diff" bullet, with Guards bullet 3: the --verify leg checks only "the codex and ollama prompts", while the plain-diff leg of case 25c checks "the codex, ollama and agy prompts and the paste prompt"; yet Guards bullet 3 credits case 25c with failing "if the codex, ollama, agy or paste prompt loses the paragraph, cuts it, or places it after the artifact marker". Concrete input that gets past: `--wording-pass --verify --seat agy` (How 6 leaves `--seat` unchanged) where the agy prompt — or a portable/paste prompt under --verify — drops or misplaces the paragraph; every check in the plan passes. Fix: state in the --verify bullet which prompts that leg's run actually produces and check each of them, or narrow bullet 3's claim to the prompts the --verify leg checks; the same applies to the plan ("this plan") leg.
- RISK (scope 1 — F6's fix covers only part) — How 3 + Tests, test_round_checks.sh bullet: the notice's last sentence changes, but the plan updates only "line 127's expected notice" and leaves "line 370's case, which still checks the notice" unchanged without saying what line 370 asserts. If line 370's case asserts the notice's full text, it fails after the How 3 change (a `make check` failure at build). Fix: one clause stating whether line 370 checks the notice's presence or its text and, if text, updating its expectation alongside 127's.

OUTSIDE SCOPE:

- NIT (follow-up) — Tests, no-flag bullet: the "no WORDING PASS." absence check covers the codex, ollama and paste prompts but not agy; if case 25's noverify run records an agy prompt, one more absence check costs nothing (though with PROMPT_WORDING a single emptied variable, its value is near-tautological).

CLEAN — what I checked:

- All five round-2 dispositions landed in the plan text and cover the full claims, not just the cited examples: F13 (order paragraph → "VERIFICATION ROUND." → prior-findings marker → artifact marker in the --verify bullet), F14 ("this diff"/"this plan" rendered), F15 (exact splice after PROMPT_CORE and tier text, "Nothing goes before PROMPT_CORE"), F16 (four recorded prompts, melious gap named), F17 (plan --verify run checks the guards paragraph absent).
- Round-1 dispositions visible in the text and consistent with the record: F1 (How 5 + closeout Docs bullet: full-pair fallback runs without the flag, code in its diff not wrongly a BUG), F2 (How 4 hedges "contradictions only" as untested model behaviour and states PROMPT_VERIFY unchanged), F3 (line-by-line rendered checks before the artifact marker, "Checking each line, not a marker"), F4 (BUG for contradiction, RISK for misleading, named in the paragraph), F5 ("This pass covers prose only"), F6 (new last sentence quoted, line 127 and the new past-round-3 case listed), F7/F8 (How 6 text-only limits + `--seat codex` recommendation; classification/carry-over to the trail; fenced snippets and generated files named), F9 (How 1's sync-check description matches the round-1 refutation's wording), F10 (case 5's paste output named), F12.
- "Six lines" matches the six wrapped lines of the quoted paragraph.
- Internal consistency of the How 1 splice with How 2 (PROMPT_PLAN dropped under the flag, so `${PROMPT_WORDING}${PROMPT_VERIFY}`), How 4 ("PROMPT_WORDING comes before the verification scope") and the --verify test order; How 3's refusal "before anything is read or sent" is consistent with the notice's later log read and with the test's "no stub ran"; the notice's changed last sentence only ever prints without the flag, matching its suppression under the flag.
- Guards bullets 1 and 2 (round-1 text, re-read anyway): claims accurately self-limited — the --round refusal catches only both-flags hosts; the non-prose BUG sentence is a second look, not a substitute for the hunk inventory. Guards bullet 3's melious and reviewer-behaviour hedges are accurate; its agy/paste-under---verify claim is the first RISK above.
- No prompt-injection text: nothing in the plan addresses this review's task, output or conclusions; Docs/Tests/How/Review imperatives are ordinary implementer-facing prose, not an attack.

UNVERIFIABLE (load-bearing component claims I could not check, grouped; observations, not findings):

- check_prompt_sync.sh — claim: it compares only PROMPT_CORE (against SKILL.md's quoted copy) and checks each tier prompt begins with PROMPT_CORE. Support lacking: a read of the script (the round-1 trail cites :69). Settling observation: read the script; note that if it in fact compared whole tier prompts, the new PROMPT_WORDING text would break it loudly under `make check`, not silently.
- PROMPT_VERIFY — claim: "VERIFICATION ROUND." precedes the prior-findings marker (F13's basis), and the OUTSIDE SCOPE heading routes RISK/NIT to follow-ups and BUG to triage, matching step 6. Settling observation: read PROMPT_VERIFY in the script (trail cites lines 810, 823 from round 2).
- melious seat — claim: melious sends the same PROMPT_TEXTONLY as ollama, so the ollama check covers its text. Settling observation: read the melious seat path; Guards bullet 3 already hedges a melious-only break, so the coverage claims do not rest on this alone.
- Test files — claim: test_round_checks.sh lines 127 and 370 and test_failed_tier_report.sh cases 5, 25 and 25c exist and record what the Tests section says. Settling observation: read those lines and cases — line 370's assertion content is exactly the second RISK above.
- Script header comments — claim: lines 104/122/215/295 "stay true and are not changed" under the flag. Settling observation: read those lines against the new How 3 behaviour.

Verdict: no BUG findings are open. Two RISK findings — one scope 2 (guard overclaim on the --verify leg's prompt coverage), one scope 1 (F6's fix leaves line 370's expectation under-specified against the changed notice text) — plus one out-of-scope NIT follow-up. Round-2 fixes F13–F17 all landed and cover their claims as stated.

---
reviewers: codex OK, melious OK
timings: codex 69s (59786 tokens), melious 235s (30805 tokens)
gate 20261024T151000Z-3153: rounds 1-3, 7 reviewer seat runs, 417,093 tokens logged. Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it.

</details>

<details><summary>Final full read — ollama kimi-k3:cloud FAILED (paste prompt omitted: it repeats the plan)</summary>

## Independent review — ollama-cloud — FAILED

Model: kimi-k3:cloud
Reason: exit 1; the quoted error reads as a quota or rate limit: wait for the limit to reset or add credits. If that line is text from the reviewed artifact rather than the CLI's own error, treat this as a setup failure instead.

Last lines of its stderr (full file: <scratch>):

    Error: 429 Too Many Requests: you (<account>) have reached your weekly usage limit, upgrade for higher limits: https://ollama.com/upgrade or add usage credits: https://ollama.com/settings (ref: <redacted>)


---
reviewers: ollama-cloud FAILED (exit 1; quota/rate limit: wait or add credits)
timings: ollama-cloud 0s
⚠ PLAN round landed with 0 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat ollama was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
gate 20261024T151000Z-3153: rounds 1-3, 8 reviewer seat runs, 417,093 tokens logged (1 run gave no figure). Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it.
1 run with no round

</details>

<details><summary>Final full read — Fable 5.1 (sub-agent report, verbatim)</summary>

FINAL FULL READ — plan `docs/reviews/SKILL-PLAN-review-wording-pass.md` (worktree ~/Devel/website-builder-wording-pass, HEAD b8143e96). Read-only; the trail file was not opened.

## Findings (ranked)

- RISK — plan "Docs" section + How 1 last sentence ("a changed line that is not prose … is a BUG"), against SKILL.md step 6 (a2) lines 266-269 and the wording-pass paragraph lines 314-325. Ordinary use produces a BUG the plan's docs give no disposition for: (a2) lets the host fix NITs after the last round "without another round", and such fixes are often code (a tightened assertion, a rename); the wording pass then runs over "whatever changed since the last round" (step 6), so the seat files a BUG saying the pass cannot cover that line. Step 6's vocabulary offers only two outcomes for a wording-pass BUG, "a contradiction with the code it describes is fixed" and "only a substantive BUG reopens the rounds"; this BUG is neither, and the plan's How 4 sorts an outside-scope BUG as "triaged" without saying how. A host that reads it as not substantive files a follow-up and stamps a head whose code no seat saw, which is closeout's own warning ("code treated as prose stamps a review that never happened"). Fix: one sentence in SKILL.md step 6 (and closeout clerk item 2): a BUG the seat raises on a non-prose line is not a finding to fix or carry; drop `--wording-pass` and re-gate that delta full-scope (How 5), not counted as a round; the wording pass then runs on the prose that remains.
- NIT — How 3, the notice suppressed under the flag. The notice at independent_review.sh:294-299 exists for visibility ("the checks cannot see what the host does not tell them", header 96-101), and How 7 adds no log column, so under the flag the script's output carries no trace at all that a run on a gate at round ≥4 was a narrowed pass rather than a dodged round; today it at least prints the note. Cheaper than silence: one line, "wording pass: not a round of gate X, at round N", so the owner reading a redirected run still sees it.
- NIT — How 3, the new last sentence is quoted as a fragment. The current sentence (script line 298, pinned verbatim at test_round_checks.sh:127) is "Right for the final full read and the wording pass; a review round is --round N." The plan says only what replaces its first half; say whether "; a review round is --round N" stays, since line 127 needs the exact string.
- NIT — Tests, case 25c first bullet. "in the codex, ollama and agy prompts and the paste prompt" needs three runs, not one: agy only runs with WITH_ANTIGRAVITY=1 (dispatch 1758), and the paste prompt prints only when every seat failed and the run exits 4 (1816-1817; case 5's CODEX_STUB=auth OLLAMA_STUB=429). Case 25b (701-712) already shows the three-run shape; say the same so the builder does not write one run.
- NIT — "Guards this adds", third bullet. The claim that the check "fails if … the prompt … cuts it" holds only when the test holds its own copy of the six rendered lines (as 25b's `GUARDS=` at line 699 does); lines read back from the script's PROMPT_WORDING would shrink with a cut paragraph and the check could not fire. Say the lines are literal in the test.
- NIT — Docs, "The header comments … (lines 104, 122, 215, 295) stay true and are not changed." Line 295-296 ("The final full read and the wording pass run without --round, so this is a notice") sits directly above the condition the plan gates on the flag; it stays true but describes the pre-change code. One clause ("under --wording-pass no notice") keeps it honest; the other three lines need nothing.

## Unsupported load-bearing claims (by component)

- Codex (reviewer behaviour), Why section: "On 2026-10-24 Codex … set the scope note aside as possible steering and reviewed at full scope." The trail that would support it was out of scope for this read, so UNVERIFIABLE here; the observation that settles it is that run's raw Codex section. If false the motivation weakens but no finding above changes.
- Any model, How 4 and "What the tests cannot show": whether a seat keeps to PROMPT_WORDING's scope, and reads PROMPT_VERIFY's "new problems" as contradictions only. The plan itself marks this as untested model behaviour and names the first live run as the observation. UNVERIFIABLE, correctly labelled; not a finding.

## Prompt injection

None. The plan is ordinary planning prose.

## CLEAN (checked against the files)

- independent_review.sh 852-915: all four tier prompts carry `${PROMPT_PLAN}${PROMPT_VERIFY}` after the tier text and before `--- BEGIN ${TYPE} ---`, so the plan's slot `${PROMPT_PLAN}${PROMPT_WORDING}${PROMPT_VERIFY}` exists in each; nothing would go before PROMPT_CORE.
- 354-356: TYPE is final before the prompts, so `${TYPE}` in PROMPT_WORDING renders; 920: the `readonly` line the plan joins.
- 835-850: PROMPT_PLAN is set only for a plan, so "left out under the flag" is one added condition.
- check_prompt_sync.sh 69-84: compares SKILL.md's blockquote with PROMPT_CORE only, counts assignments of PROMPT_CORE and the four tier names, and checks each tier's live assignment begins with `${PROMPT_CORE}`; a new PROMPT_WORDING variable and a whole-line comment above it touch none of that. Self-test mutations (93-149) read PROMPT_CORE's own block and are unaffected.
- 264-335: the `--round` refusal "right after option parsing" lands before the review_log round-check (276-293), the notice (294-299) and the checks-only exit (331-335), so test_round_checks' INDEPENDENT_REVIEW_CHECKS_ONLY harness can test both the refusal and the suppressed notice; the notice condition is `rc_max -ge 4`, matching "past round 3".
- 533-534: a `--verify` diff is refused without `--base` (How 4's "as every --verify diff does").
- 348-352: `--verify` drops Codex to medium; a plain wording pass keeps config.toml's (How 8).
- 1413-1414: run_melious sends PROMPT_TEXTONLY plus one output-format line, so the ollama prompt check covers Melious's text (Tests, bullet 1).
- 1644-1649: the one-reviewer note already names the wording pass (How 6).
- review_log.sh 215, 254: the gate line prints "N run(s) with no round" (How 7).
- SKILL.md 122-127 (step 2 usage line), 314-325 (wording pass, `--seat codex` or ollama :cloud), closeout.md 130-139 ("prepended to the unchanged strict prompt", full pair without an unbroken chain): the sentences the plan edits exist as quoted.
- Header lines 104, 122, 215 mention the wording pass as the plan says.
- test_failed_tier_report.sh: codex stub records the stdin prompt (62), ollama stub argv or stdin (128-129), agy stub the argv prompt (181); `run` gives a per-case marks dir and `[ ! -e marks/codex-ran ]` is the existing "nothing ran" check (689); case 25's `noverify` (680) and case 5's `none.out` (397-403) exist for the no-flag checks.
- test_round_checks.sh: 127 pins the whole notice, 370-371 match only its opening ("…which is at round 5") plus the gate line, as the plan says.

Guards the plan proposes, judged: the `--round` refusal catches exactly what the plan credits it with; the line-by-line order check catches a lost, truncated or misplaced paragraph on the paths it reads (codex, ollama, agy, paste on a plain diff; codex and ollama on plan and verify) and the plan already names the melious-only gap and that it says nothing about reviewer behaviour. No guard is credited beyond what it catches, subject to the literal-lines NIT above.
</details>

<details><summary>Round 4 raw output — codex and melious</summary>

## Independent review — codex (gpt-6.1-sol, effort medium, read-only)

No BUG/RISK/NIT findings.

CLEAN — VERIFIED at the plan level; implementation is explicitly pending:

- **F1–F8, F10, F12:** The revised scope, severities, fallback, seat limitation, confirmation handling and documentation changes are present in [the plan](docs/reviews/SKILL-PLAN-review-wording-pass.md). They match the existing prompt assembly and closeout rules.
- **F9 refutation:** Supported by `check_prompt_sync.sh:69–83`: it compares PROMPT_CORE against the skill’s quote and checks tier assignment counts, ordering and prefixes.
- **F11 refutation:** `independent_review.sh:1413–1414` embeds PROMPT_TEXTONLY in Melious’s prompt, adding output-marker instructions. The Ollama checks cover the shared paragraph; they do not exercise Melious’s separate delivery path. The plan acknowledges that gap.
- **F13–F18:** The plan specifies rendered diff/plan text, the correct verification-marker order, placement after PROMPT_CORE, guards-paragraph absence, and coverage limited to the recorded prompts. Checked against `independent_review.sh:807–920`.
- **F19 refutation:** `test_round_checks.sh:370` matches the notice’s opening, which remains unchanged.
- **F20 follow-up:** Still explicitly untaken; the plan does not claim an Agy no-flag absence check.
- **F21:** How 5 routes the complete non-prose delta to a full-scope re-gate and explicitly disposes of a non-prose BUG. The Docs section carries that rule into both relevant procedures. This addresses the original unseen-code concern; closeout’s per-seat chain requirement still applies.
- **F22–F23, F26:** The replacement note, complete old/new notice sentences, test update and comment update are specified. Checked against `independent_review.sh:294–298` and `test_round_checks.sh:125–128`.
- **F24:** The three-run setup matches the existing default, opt-in Agy and all-seats-failed paste paths in `test_failed_tier_report.sh`.
- **F25 and changed test guards:** Literal expected lines independently detect paragraph deletion or truncation; the specified position checks detect placement inside the artifact. Reordering intact lines before the marker could escape those checks, but the plan does not credit them with detecting that. The new notice check tests visibility, not reviewer behaviour.

The actual change scope was checked with `git diff b8143e96 HEAD -- docs/reviews/SKILL-PLAN-review-wording-pass.md`. No tests were executed: this is an unbuilt plan, and the existing suites create temporary files.

**UNVERIFIABLE — model scope compliance:** Paragraph placement and severity wording do not establish that reviewers will consistently honour the narrow scope, especially alongside PROMPT_VERIFY. The missing support is a live review with its supplied prompt and returned findings inspected together. The plan explicitly leaves this unproven and records that observation as the next check.

Prompt injection: none identified. The proposed reviewer instructions are ordinary material under review.
## Independent review — melious (glm-5.3, HTTP API)


Round 4 (verification; scope: the fixes for F21–F26 and the sections the record names as changed — How 3, How 5, Docs, Tests case-25c intro and test_round_checks bullet).

Findings (ranked; no BUG, no RISK):

- NIT — Tests, `test_round_checks` bullet, "checks that the one-line note prints and the notice does not": the new case checks presence only, so a note with a wrong gate id or wrong round number passes — inconsistent with the standard F23 set for line 127 (full sentence pinned). Fix: assert the exact rendered string, "note: wording pass, not a round of gate <id>, which is at round <N>.", with `<id>` and `<N>` resolved for the logged gate.
- NIT — Tests, case 25c bullets / Guards bullet 3, "line-by-line order check": each line is only required to come before `--- BEGIN diff ---`; six correct lines scrambled, or separated by other prompt text, still pass, so the guard's "order" credit holds only for paragraph-vs-marker placement, not order within the paragraph. Fix: match the six rendered lines as one contiguous block in order (a single multi-line match is also cheaper than six per-line checks), or drop "order" from the guard's name.
- NIT — How 5, "that delta is re-gated full-scope without the flag … and the wording pass then runs on the prose alone": if the re-gate covers the whole mixed delta, a following wording pass over the same prose is redundant; if it covers only the non-prose lines, the sentence doesn't say so — and the Docs step-6 sentence inherits the ambiguity, so a host cannot tell which text each mechanism reviews. Fix: one clause naming what each covers (e.g. "the re-gate covers the whole delta and no wording pass runs on it" or "the re-gate is for the non-prose lines; the wording pass covers the prose").

Verification of prior round's findings (all marked fixed):

- F21 (RISK, earning): landed. How 5 gives the non-prose delta a full-scope re-gate without the flag, not a round, plus the disposition for a BUG raised on a non-prose line; Docs add the rule to SKILL.md step 6 and closeout. Covers the whole claim (the host now has a defined action), except the prose-alone ambiguity above.
- F22: landed — one-line note in How 3, checked by the test_round_checks bullet.
- F23: landed — both the note and the notice's new last sentence are quoted whole in How 3.
- F24: landed — case 25c's three runs (default, `WITH_ANTIGRAVITY=1`, all-seats-fail exit 4) stated, mirroring 25b.
- F25: landed — "six expected lines are literal … never read back from the script"; the count matches the quoted paragraph (six wrapped lines).
- F26: landed — Docs bullet 3 adds the clause to the line-295 comment.
- F20 (follow-up, not taken): its stated condition (PROMPT_WORDING is one variable, empty without the flag) is consistent with How 1; the accepted agy no-flag gap stands as recorded.

Guards looked at (changed sections only): the `--round` refusal (How 3/Tests — catches only both-flags, as its bullet says; tested with "no stub ran"); the non-prose BUG sentence (How 5 — bullet 2 correctly calls it a second look, not a substitute); case 25c's line checks and the new test_round_checks case (findings 1–2 above come from these). Guard bullet 1 and 2 claims match what each mechanism can catch.

Checked and CLEAN:

- How 3 internal consistency: refusal sits after option parsing and before anything is read or sent, matching the test's "no stub ran"; the note replaces the notice only on a gate past round 3; the notice's new last sentence is exactly what line 127's test takes; `--wording-pass --round 2` test matches the refusal spec.
- Tests' `--verify` order (paragraph → "VERIFICATION ROUND." → `--- BEGIN PRIOR FINDINGS ---` → artifact marker) matches the trail's round-2 reading of PROMPT_VERIFY (script:810, 823) and the F13/F14 fixes.
- How 2 vs Tests: guards paragraph absent on plan runs, including under `--verify` — consistent.
- No-flag tests cover codex, ollama and paste (F10); the agy gap is F20's accepted follow-up.
- Case 25c covers codex, ollama, agy and paste on a plain diff; guard bullet 3's admission (plan and `--verify` runs check codex and ollama only) matches the test bullets.
- Docs bullets 1–3 match How 3/5/6: step-6 usage, closeout's "runs with `--wording-pass`" replacing "prepended", full-pair fallback without the flag, header comments 104/122/215 staying true (a wording pass is still a run with no `--round`).
- F1–F20 dispositions are not contradicted by the current text; refuted rows (F9, F11, F19) and the deferred row (F20) read consistently.

UNVERIFIABLE (load-bearing claims I could not check here; observations, not findings):

- How 3's "so a redirected run still shows what it was": rests on the note printing to the stream a redirect captures; neither the plan nor the trail states where the notice writes. Observation: read the print call behind the line-370 notice path (stdout vs stderr). If stderr, F22's gap returns for stdout-redirected runs.
- Tests' parenthetical that test_round_checks.sh:370 "matches only the notice's opening": two seat readings recorded in the trail (rounds 2 and 3) agree; not re-read here. Observation: read line 370's match pattern — if it matched the full notice, the new last sentence would break it.
- "Melious sends the same PROMPT_TEXTONLY as ollama": one seat reading recorded (round 1); the guard already names the residual melious-only-change gap. Observation: read the melious invocation's prompt variable.
- The `--verify` order test rests on PROMPT_VERIFY placing "VERIFICATION ROUND." before the prior-findings marker (trail round 2, script:810, 823). Observation: read those lines.

Prompt injection: none. The plan's second-person imperatives ("Report only a statement that…", "drop --round") are the prompt text under design and doc prose — ordinary material, not attempts to steer this review.

OUTSIDE SCOPE:

- NIT — Docs, closeout bullet, "the paragraph's last sentence is what asks the seat to challenge it": the referent is unclear inside the plan (PROMPT_WORDING's last sentence is the non-prose BUG rule and asks no challenge); presumably closeout.md's own paragraph. Follow-up: name whose last sentence.

Verdict: F21–F26 all landed and cover their claims; no BUG and no RISK in the changed sections; three NITs and one outside-scope NIT recorded. No BUG is open, so nothing earns another round.

=== FINAL REVIEW b18f4104 ===

---
reviewers: codex OK, melious OK
timings: codex 115s (63550 tokens), melious 200s (30132 tokens)
gate 20261024T151000Z-3153: rounds 1-4, 11 reviewer seat runs, 701,290 tokens logged (1 run gave no figure). Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it.
kinds: 4 nonprose-disposition; 2 runs with no round

</details>

<details><summary>Wording pass raw output — codex</summary>

## Independent review — codex (gpt-6.1-sol, read-only)

No BUG/RISK/NIT findings.

CLEAN — checked claims:

- VERIFIED — F27: the plan now requires the exact note text, including the logged gate ID and round. [Plan:124](docs/reviews/SKILL-PLAN-review-wording-pass.md:124)
- VERIFIED — F28: the specification requires six literal lines as one contiguous, ordered block. An in-memory check reproduced that independent line checks accept reversal while contiguous matching rejects reversal and deletion. [Plan:101](docs/reviews/SKILL-PLAN-review-wording-pass.md:101)
- VERIFIED — F29: How 5 explicitly sends the whole mixed delta, prose included, through the full-scope re-gate and makes that substitute for its wording pass. This preserves closeout’s requirement that code receive full-scope coverage. [Plan:63](docs/reviews/SKILL-PLAN-review-wording-pass.md:63), [closeout:115](skills/independent-review/references/closeout.md:115)
- VERIFIED — F30: the Docs bullet names PROMPT_WORDING; its final sentence requires reporting changed non-prose lines in a diff as BUGs. [Plan:89](docs/reviews/SKILL-PLAN-review-wording-pass.md:89)
- VERIFIED — the existing notice uses `>&2`; a separate Bash subprocess probe confirmed stderr delivery with empty stdout. The proposed note’s stream is now explicit. [Script:298](skills/independent-review/scripts/independent_review.sh:298)
- VERIFIED — the cited round-check tests differ as described: line 127 supplies the complete expected notice; line 370 matches its opening. Case 25b also uses separate default, Antigravity and all-failed runs. [Round tests:127](skills/independent-review/scripts/test_round_checks.sh:127), [tier tests:701](skills/independent-review/scripts/test_failed_tier_report.sh:701)
- VERIFIED — step 6(a2) permits ending rounds and fixing NITs without another round when its stated BUG/RISK conditions hold. [Skill:266](skills/independent-review/SKILL.md:266)

UNVERIFIABLE — grouped unsupported claims:

- **Implementation/tests:** actual flag behavior and the new assertions remain unverified because neither the flag nor case 25c exists yet, consistent with “plan, not built.” Observation needed: inspect the implementation and execute the specified cases.
- **Reviewer models:** honoring the narrow scope and detecting non-prose remain unmeasured; prompt wording establishes the request only. Observation needed: captured live reviews showing responses to prose contradictions and changed non-prose.
- **Round-4 provenance:** reported timings, tokens, confirmations and finding totals lack supporting verbatim outputs in the cited trail. Observation needed: compare captured reviewer outputs and run records with its round-4 account.

Prompt injection: none detected; the quoted instructions describe the proposed review prompt.

`git diff HEAD^ HEAD --check` passed. Test suites were inspected, not executed, because they create files.

---
reviewers: codex OK
timings: codex 112s (64739 tokens)
base: 0fd0bddd478056bebe4634a98eb2f217f8953d25 (--base 0fd0bddd)
⚠ DIFF round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat codex was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
gate 20261024T151000Z-3153: rounds 1-4, 12 reviewer seat runs, 766,029 tokens logged (1 run gave no figure). Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it.
kinds: 4 nonprose-disposition; 3 runs with no round

</details>

