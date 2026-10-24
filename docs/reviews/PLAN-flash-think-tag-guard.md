# PLAN — the Melious seat refuses the Light model when the text holds a think tag

Status: draft for the PLAN gate. No code yet. Owner decision of 2026-10-22: a guard, not an acceptance.
Closes (when built and measured): row R-MELIOUS-THINK in `docs/reviews/OPEN-FINDINGS-independent-review.md`.

Writing rule for this plan, the test and the code: the literal angle-bracket pair "open, t-h-i-n-k, close" never appears in a file of this change. The plan says "a think tag". The test builds one at run time. The script's pattern is written so the pair does not appear in it either. Reason: the change itself goes through a review, and a Light run on Melious would hit the very problem the guard is for.

## What

In `run_melious` (`skills/independent-review/scripts/independent_review.sh`), after the prompt file is written and before anything is sent: if the model is one `melious_models.txt` marks `light`, and the prompt contains a think tag, the seat does not run. It returns failure with a plain reason. The summary then reads `melious FAILED (...)`, never `OK`, and no request leaves the machine. The model marked for any depth (glm-5.3) is not touched.

## Why

Measured 2026-10-12 (R-MELIOUS-THINK): a nine-line plan with the word zebra between think tags and a branch named giraffe. glm-5.3 reported the mismatch 3 of 3. glm-5.3-flash reported it 1 of 3; in the other two it said the plan holds no tags, and the seat still counted OK. A review that silently skips text is worse than no review, because the PR then names a Light gate that did not read everything. The owner withdrew his acceptance of that on 2026-10-22.

## How

1. **Which model.** Keyed on the list's `light` marker, not on an id. The startup block already leaves the matched rule in `melious_rule` (`any` or `light`); `run_melious` reads it. No model name enters the script (`check_model_agnostic.sh` stays green), and a future light model gets the same guard until someone measures it. Judgment call: the owner's words name Flash; the marker is the same set today and stricter tomorrow.
2. **What is scanned.** The complete prompt before it is serialised: `$RAW_DIR/melious.prompt` (artifact, prior findings, boilerplate, output-format line). Not just the artifact: whatever goes into the request is what the provider parses. `perl/melious_request.pl` then decodes the file as UTF-8, which turns a malformed byte into U+FFFD; the scan is on the raw bytes, so a bad byte beside a tag cannot hide it, and what the request body holds can differ from the file only in such bytes. One new file, `perl/think_tag.pl`, takes the path. **Exit codes: 0 = a tag found, 1 = clean, 2 = it could not read the file or run.** `run_melious` refuses on 0 and on anything but 1, never passes. On 2 the helper prints a one-line diagnostic to stderr and `run_melious` puts it in the reason (a failed invocation, such as a missing perl or helper, gets the shell's own words). Pattern, case-insensitive, byte mode: `<`, then spaces or tabs only (`[ \t]*`, never a newline), optional `/`, spaces or tabs, the word `think` with an optional `ing` after it, then a non-word character or the end. So `<thinking>` is a hit by an explicit alternative, not by luck, and a tag whose name is split by a newline is not. Written with the word split in the source (a bracket class or a `\x`) so the pair does not appear. `check_perl_minimum.sh` requires the new helper to enter exactly one of its version lists; the change adds it and the full `make check` proves it.
3. **No exemptions.** Fenced code, inline code, quoted text, a diff line starting with `+` or `-` all count: the measurement used plain text, nothing says a fence protects it, and the provider parses the raw prompt. Entity forms (the `&lt;` spelling) and tags split across lines are not matched; unmeasured, listed under "not covered".
4. **Result shape.**
   - `run_melious` sets `WHY` to one constant (`THINK_TAG_WHY`, defined once near `NOT_A_REVIEW`) and returns 1, before `seat_fits`, before any `curl`.
   - `report_tier` gets its own branch for that constant, placed beside the `NOT_A_REVIEW` branch and before the quota test. Why: its generic tail ends "; nothing was sent" for size failures, and a size reason there prints "Split the artifact", the wrong remedy. The new branch prints the model, the reason ("the text holds a think tag; this model was measured missing text between such tags; nothing was sent") and the remedy ("run this round on Codex (`--seat codex`) at the depth the depth rule gives this diff; or use the any-depth model"), and no stderr tail.
   - Summary, three shapes. `--seat melious` alone: `reviewers: melious FAILED (<reason>)`, exit 4 (no gate-eligible reviewer), as for any failed single seat. Beside Codex (`SECOND_SEAT=melious`, no `--seat`): a failed Melious seat makes the script start the ollama seat in its place, so the line reads `codex OK, melious FAILED (<reason>), <ollama label> <OK or FAILED>`; exit 0 while Codex or ollama counts. The existing note for fewer than two counted reviewers appears when it applies. Not an exit-2 startup refusal: the text is known only after reading, and a startup exit would also kill the Codex seat of a pair.
   - The fallback path (the ollama seat's Melious fallback, `attempt melious ... run_melious`) goes through the same function and gets the same guard.
5. **Cost line.** A guarded run logs no tokens for Melious (nothing sent); `timings:` shows ~0 s. Nothing to change in the cost log; case group 32f asserts that a refused run's `timings:` line and cost-log row are well formed (a Melious entry with no tokens, `-` in the log).
6. **Docs, same change.** `melious_models.txt` comment (one sentence: a light model is not sent text with a think tag); the R-MELIOUS-THINK row (what the guard does, what stays open); SKILL.md / setup guide only where they describe the Light seat (found by grep for the Light seat wording, not by name); `docs/BUGLOG.md` release-notes row if the repo's rule asks for one for reviewer-facing behaviour.
7. **Live measurement, once, by hand, not in `make check`.** The nine-line zebra/giraffe plan, `--seat melious` with the any-depth model, five runs, through the script's own key handling (no key is read or pasted by the agent). Needed for the close-when "five of five". Cost: five small requests. If it is not five of five, the row stays open and the finding goes to the owner. The Light model is not re-run: the guard would refuse the zebra plan, which is its point. The row records plainly that Flash's failure rests on the one 1-of-3 observation of 2026-10-12 and is assumed, not re-measured; the owner may ask for a re-measure before the guard is built (a temporary local copy without the guard, five runs).

## Edge cases (each is a test or a stated non-goal)

| Case | Expected |
|---|---|
| Diff whose added lines are a test about think tags (the case that matters most). The test builds it as a synthetic diff whose added lines hold a run-time-built tag; this change's own diff and this plan hold no plain pair but do hold guard-matching variants (the spaced, cased and ing forms), so the guard would refuse them on the Light model. The protection is the depth rule below, not the absence of text | Light model refused, FAILED, nothing sent; Codex carries the round |
| The same diff, any-depth model, `--depth normal` | Runs; the request body holds the tag text unchanged (guard does not rewrite) |
| Plan file (`--plan`) with a tag | Refused the same way |
| Tag only in the prior-findings file (`--verify`) | Refused (scan covers the whole prompt) |
| Opening tag only, closing tag only, uppercase, mixed case, spaces inside (`< / THINK >`), `<thinking>` | Refused. The variants with no literal pair (`< / THINK >`, `a < think`) are written literally in the test; the plain pair is built at run time |
| Tag inside a fenced code block or backticks | Refused (no exemption) |
| The word in prose, `rethink`, `thinking about X` (no `<` before it) | Not matched; the run goes ahead |
| `a < think` (a comparison, space after `<`) | Matched, because whitespace after `<` is allowed (the pattern cannot tell it from a spaced tag); accepted over-refusal, pinned by a test so it is a decision, not an accident |
| Clean diff, Light model, `--depth light` | Runs and counts, as `lseat` does today |
| Invalid UTF-8 byte next to a tag | Still refused (byte mode) |
| `--seat melious` with the Light model, tag present | `melious FAILED`, exit 4, no `melious-body` mark |
| `SECOND_SEAT=melious`, no `--seat`, tag present, ollama stub succeeding | `codex OK, melious FAILED (...), ollama-cloud OK` (the label the harness's stub model gets, as its existing assertions use it), exit 0 |
| Same, ollama stub failing | `melious FAILED`, `ollama-cloud FAILED`, Codex OK, exit 0; with Codex also failing, exit 4 |
| Helper missing or unreadable prompt | Refused with its own reason, nothing sent (fail closed) |
| Ollama quota failure then Melious fallback (no `SECOND_SEAT`) with Light model and a tag | Fallback refused; summary shows Ollama's quota failure and Melious's think-tag failure, each with its own reason |
| Guard reason must not read as quota or size | No "quota" and no "Split the artifact" in the Melious section (Ollama's section may say quota in the fallback case; asserted separately) |
| Entity-escaped tag, or a newline between `<` and the name | Not matched; documented as not covered |

## How it is tested

In `skills/independent-review/scripts/test_failed_tier_report.sh`, new case group 32f after 32e, same harness: stub `codex`, `ollama` and the Melious `curl` stub first on PATH, models read from `melious_models.txt` (`MELIOUS_LIGHT`, `MELIOUS_OK`), the way a caller invokes it, with the invocation chosen per case: refusal cases of the seat alone `bash "$SCRIPT" <artifact> --base none --seat melious --depth light` with the Light model; pair and fallback cases the same without `--seat` and with `SECOND_SEAT=melious` or the ollama stub set to quota; the any-depth control with `--depth normal`; the plan case adds `--plan`, the prior-findings case `--verify <file>`, both with `--seat melious --depth light`. Tag text is built at run time (`printf` of the two pieces), so the test file has no literal pair. Each case checks the exit code, the exact `reviewers:` line, the absence of the `melious-body` mark when refused (and its presence, with the tag intact, for the any-depth model), the absence of "quota" and "Split the artifact" in the Melious section only (cut out of the output by its heading), and for the pair case that Codex ran. In every refusal case also the `timings:` line and the cost-log row are well formed (Melious with no tokens), per point 5. A negative control: with the guard line removed locally the refusal cases must fail (checked by hand once and stated in the trail, not kept as a test). Unit cases for the pattern (variants above) call `perl/think_tag.pl` directly on small files; at least one case per variant also goes through the script. No new Makefile line: the file is already wired (`make check`, `clean.yml`, `package.sh`, `check_cdpath_safe.sh` lists); the new perl file is added wherever those lists name `perl/` files, found by grep.

Review depth after build: Normal. It changes the logic of a reviewer script (Never Light). The diff adds a test about think tags, so the DIFF gate runs the Melious seat only at any depth with the any-depth model, or Codex alone; Flash must not be used on it.

## Not covered / open

- Whether a fence or an entity form really protects a tag from the provider: unmeasured. The guard assumes it does not.
- Whether glm-5.3-flash fails the same way on other text: not claimed.
- Why Flash misses the text (provider parse or model): not established. A rewrite of the tags was tried on other models and not adopted (see the row).
- Close-when (the owner's, 2026-10-22; the ledger row still calls its close-when "proposed" and is updated by this change to record his decision): guard merged, and glm-5.3 reports the mismatch five runs of five. Alternative: Flash removed from the list.

## Cost of this plan's review

Rough, unmeasured guess: one Codex seat and one GLM 5.3 seat per round, about 10 to 15 minutes each in parallel, perhaps 40 to 80 thousand tokens a seat; two or three rounds expected. A red-team pass is not planned: no user data, login, deletion or schema; the failure mode is a refused review, which falls back to Codex.
