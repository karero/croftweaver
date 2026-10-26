# Review trail: PLAN gate, SKILL-PLAN-second-seat-no-fallback.md

Gate: PLAN, depth Normal (a plan for a review script's logic). Seats run as two separate commands
(`--seat codex`, `--seat melious`) with the same `--round`, by the maintainer's rule of
2026-10-26; fresh-eyes on a mid-tier host-family model in round 1. No red team (no server, data,
money or deletion).

| Round | Artifact | Seats | Findings | Disposition |
|-------|----------|-------|----------|-------------|
| 1 | plan at 550a1cd8, evidence = script/test/doc excerpts | codex OK (362 s, 74,213 tokens), melious OK (318 s, 33,377 tokens), fresh-eyes OK (~123k tokens) | 2 BUG, 5 RISK, 8 NIT (F1-F15) | all fixed in the next revision |
| 2 | plan at 7bcd8c2f, `--verify` F1-F15 | codex OK (435 s, 69,762 tokens), melious OK (559 s, 50,719 tokens) | 1 BUG, 2 RISK, 3 NIT (G1-G6) | all fixed in the next revision |

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
