# Review trail: PLAN gate, SKILL-PLAN-melious-no-balance-codex-alone.md

Gate: PLAN, depth Normal (a plan for a review script's logic). Pair run as one command
(`SECOND_SEAT=melious`). No red team (no server, data, money or deletion).

| Round | Artifact | Seats | Findings | Disposition |
|-------|----------|-------|----------|-------------|
| 1 | plan at 87d446ee, evidence = script/test/doc excerpts | codex OK (173 s, 57,596 tokens); melious FAILED, out of balance (`Required: 156, Available: 0`): Codex alone | 2 BUG, 2 RISK (F1-F4) | all fixed in the next revision |
| 2 | plan at 9191a353, `--verify` F1-F4 | codex OK (140 s, 53,910 tokens) verified F1-F4; melious FAILED, out of balance: Codex alone | 1 RISK (G1) | fixed; no BUG, so the rounds end (SKILL.md step 6(b)) |

**Result: CLEAN after 2 rounds, 5 findings (2 BUG, 3 RISK), Codex alone in both rounds (melious out of balance), 111,506 tokens logged.** No wording pass: the only change after round 2 adds one test case.

## Round 2 findings (Codex)

- G1 RISK: the tests would pass a classifier needing both the code and the message text. Fixed: new test `mcodeonly` (right code, unrelated message) and mutation (a2).

## Round 1 findings (Codex)

- F1 BUG: matching "insufficient balance" in the error text can be set by an echoed artifact. Fixed: decide on the provider's structured `error.code` (`billing_insufficient_balance`) in `melious_stream.pl` (new exit 10); new test `mechoed`.
- F2 BUG: in the ollama-fallback mode the new reason ("round stands on Codex alone") would contradict the kept degraded note. Fixed: the rule's wording applies only with `SECOND_SEAT=melious` or `--seat melious`; the fallback says "add credits" and keeps its note.
- F3 RISK: `MELIOUS_NO_BALANCE` uninitialised under `set -u`. Fixed: initialised to 0 beside `CODEX_OUTCOME`.
- F4 RISK: SKILL.md would still call a Codex-alone round degraded. Fixed: one sentence under "The standard pair".
- Not acted on: two UNVERIFIABLE notes (capture provenance; the owner's words). The plan now names the dates of the real captures; the owner's words come from the brief of the session that met the failure.
