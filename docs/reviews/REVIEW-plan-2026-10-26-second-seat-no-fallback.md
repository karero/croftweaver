# Review trail: PLAN gate, SKILL-PLAN-second-seat-no-fallback.md

Gate: PLAN, depth Normal (a plan for a review script's logic). Seats run as two separate commands
(`--seat codex`, `--seat melious`) with the same `--round`, by the maintainer's rule of
2026-10-26; fresh-eyes on a mid-tier host-family model in round 1. No red team (no server, data,
money or deletion).

| Round | Artifact | Seats | Findings | Disposition |
|-------|----------|-------|----------|-------------|
| 1 | plan at 550a1cd8, evidence = script/test/doc excerpts | codex OK (362 s, 74,213 tokens), melious OK (318 s, 33,377 tokens), fresh-eyes OK (~123k tokens) | 2 BUG, 5 RISK, 8 NIT (F1-F15) | all fixed in the next revision |
| 2 | plan at 7bcd8c2f, `--verify` F1-F15 | codex OK (435 s, 69,762 tokens), melious OK (559 s, 50,719 tokens) | 1 BUG, 2 RISK, 3 NIT (G1-G6) | all fixed in the next revision |
| 3 | plan at e3bceb6c, `--verify` G1-G6 | codex OK (289 s, 89,571 tokens), melious OK (354 s, 44,539 tokens) | 1 BUG, 1 RISK (both seats), 5 NIT (H1-H7) | H3 refuted (line 404 normalizes `SECOND_SEAT`); rest fixed. H2 changed the build's test plan, so round 4 is earned (`--earned-by mutation-coverage`); H1 is wording, for the wording pass |
| 4 | plan at a1d091d1, `--verify` H1-H7, `--earned-by mutation-coverage` | codex OK (396 s, 64,641 tokens), melious OK (477 s, 53,159 tokens) | 1 BUG, 3 NIT (I1-I4) | all fixed; I1 is wording; no RISK and no substantive BUG, so no round 5 is earned |
| final full read | plan at aa5de2c4, whole | fresh Opus pass (host family, stronger than round 1's fresh-eyes; no ollama model, by the maintainer's rule) (~166k tokens) | 1 BUG (low impact), 7 NIT (J1-J8) | all fixed; J1 leaves the conclusion unchanged, so wording |
| wording pass | delta a1d091d1..12011801, `--wording-pass` | codex OK (530 s, 77,936 tokens) | 4 BUG (K1-K4) | all fixed; K4 (a fenced snippet changed) sends the delta to a full-scope re-check |

Round 1 findings, one line each:

- F1 BUG (fresh-eyes): `t11f` and `t12` also expect ollama to stand in. Fixed: added to "Changed", plus a grep step.
- F2 BUG (Codex): Antigravity ignored in "Codex alone" and the exit rule. Fixed: gate line only when Codex is the only seat counted; exit stated over all seats; `sagy` test.
- F3 RISK (Codex and Melious): the no-ollama checks could not fail with `OLLAMA_MODEL` unset. Fixed: those checks set it to the stub tag.
- F4 RISK (Melious): gate line under `--first-success`. Fixed: excluded; `sfirstcodex` test.
- F5 RISK (fresh-eyes): parsing `SUMMARY`. Fixed: `report_tier` keeps the Melious outcome.
- F6 RISK (fresh-eyes): condition and order. Fixed: stated in full, checked before the generic branch.
- F7 RISK (fresh-eyes): other `OLLAMA_MODEL` readers. Fixed: listed.
- F8-F14 NIT: setup-guide scope, `OLLAMA_RAN` removed, `--local-only` predicate, `sstop` on the default seat, mirror case, `sfirstsucc` wording, stub-marker control. All fixed.
- F15 NIT: cost and user claims. Fixed: labelled as not checked here or as judgment.

Round 2 findings, one line each (F1-F15 confirmed fixed by both seats, except the parts below):

- G1 BUG (Codex): planned docs still said "Codex-only" and "one-reviewer rounds". Fixed: "not replaced; the round reports whichever seats counted".
- G2 RISK (Codex): moved `sstop` lacked a completion marker. Fixed: the stub writes a "finished" mark; the test asserts it is absent.
- G3 RISK (Melious): `snodetect`'s no-`ollama-ran` clause could not fail. Fixed: dropped; the model-set rule names its checks.
- G4-G6 NIT (Melious): SKIPPED Melious gets the gate line; `melious_counted` removed; `sboth` expects the gate line, `sreuse` dropped. All fixed.

Round 3 findings, one line each (G1-G6 confirmed fixed by both seats, except G1's other sentence, H1):

- H1 BUG (Codex): "Who loses what" still overstated. Fixed: reworded (wording; goes to the wording pass).
- H2 RISK (Codex and Melious): the mutation claim credited checks the named mutations cannot break. Fixed: one mutation per check group, in a table.
- H3 NIT (Melious): default `SECOND_SEAT` not normalized. REFUTED: `independent_review.sh:403-404` sets it to `ollama` when unset.
- H4-H7 NIT (Melious): `--seat ollama` detect test added; `melious_pid` removed; grep terms widened; generic note claim narrowed.

Round 4 findings (H1-H7 confirmed fixed by both seats; H3's refutation upheld by both):

- I1 BUG (Codex): Change 2's summary said `SECOND_SEAT=melious` never reads `ollama list`, against `sseatollama`. Fixed: wording names `--seat ollama` as the exception (the predicate was already right).
- I2 NIT (Codex): moved `sstop` duplicated `mstop` (test line 1288). Fixed: `sstop` dropped, `mstop` gains the finished mark.
- I3 NIT (Melious): grep terms missed `ollama-cloud FAILED`. Fixed: bare `ollama-cloud`, and the sweep is called best-effort.
- I4 NIT (Melious): nothing pinned the gate line's absence under `--seat`. Fixed: `sseat` gains that check, in the mutation table.

Final full read findings:

- J1 BUG (low impact): the `OLLAMA_MODEL` readers list missed lines 1657, 1703 and 1848. Fixed: listed, each with why it does not fire; the conclusion was already right.
- J2 NIT: the live check would write to the real cost log. Fixed: `REVIEW_LOG=<scratch file>`.
- J3 NIT: `t11f`/`t12` reasons are size and length, not "setup". Fixed.
- J4 NIT: the gate line's rerun advice ignored the seat's own remedy. Fixed: points to the FAILED section first.
- J5 NIT: garbled sentence in Change 1. Fixed.
- J6 NIT: Cost said 2-3 rounds. Fixed: actual spend.
- J7 NIT: the new default-detect test was redundant. Fixed: dropped; the mutation row names `listfailauto`, `pair`, `t10a`.
- J8 NIT: `--seat codex` with `SECOND_SEAT` unset was untested. Fixed: `sseatnodetect` runs both ways.

Wording pass findings:

- K1 BUG: a scratch `REVIEW_LOG` with `--round 1` still starts a new gate. Fixed: the live check runs with no `--round`.
- K2 BUG: the gate line pointed to a FAILED section that a SKIPPED seat does not have. Fixed: "fix what the melious section above names".
- K3 BUG: Cost said the wording pass was spent. Fixed.
- K4 BUG: the delta changed a fenced snippet, outside a prose-only pass. Done: the delta is re-checked at full scope (SKILL.md step 6).
