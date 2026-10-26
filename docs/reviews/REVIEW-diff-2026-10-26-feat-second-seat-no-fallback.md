# Review trail: DIFF gate, feat/second-seat-no-fallback

Gate: DIFF, depth Normal (changes a review script's logic and its tests). Plan:
`SKILL-PLAN-second-seat-no-fallback.md` (PLAN gate clean). Seats run as two separate commands
(`--seat codex`, `--seat melious`) with the same `--round`, by the maintainer's rule of 2026-10-26;
fresh-eyes on a mid-tier host-family model in round 1. Artifact: `git diff 7c7d4073...HEAD -- .
':(exclude)docs/reviews/'`. Evidence: the suite, `make check`, the eight mutation runs and the live
check, sent with `--evidence`.

| Round | Artifact | Seats | Findings | Disposition |
|-------|----------|-------|----------|-------------|
| 1 | 7c7d4073...a49bd775 | codex OK (239 s, 66,505 tokens), melious OK (229 s, 30,302 tokens), fresh-eyes OK (~112k tokens) | 3 BUG, 3 NIT (D1-D6) | all fixed |
| 2 | a49bd775..f5656e54, `--verify` D1-D6 | codex OK (103 s, 47,777 tokens), melious OK (99 s, 10,070 tokens; no findings) | 1 BUG (E1) | fixed |

Round 1 findings:

- D1 BUG (Codex): a round-1 rerun with `--round 1` starts a new cost-log gate. Fixed: the gate line and setup guide say to leave `--round` off at round 1; `sfall` checks the text.
- D2 BUG (Codex): SKILL.md overstated when "Codex alone" prints. Fixed.
- D3 BUG (Codex): the stub's `ollama-listed` mark came after the `listfail` exit. Fixed: written first.
- D4 NIT (Melious): the gate line dropped Antigravity's remedy when it failed too. Fixed: "Each FAILED or SKIPPED section above names its remedy".
- D5 NIT (Melious): "ollama is never called" overbroad. Fixed: "the pair never calls ollama".
- D6 NIT (fresh-eyes): long line in SKILL.md. Fixed.

Round 2 (D1-D6 confirmed fixed by both seats):

- E1 BUG (Codex): the gate line promised a SKIPPED section, which `report_tier` never prints. Fixed: "Each FAILED section above names its remedy, and a SKIPPED seat's reason is in the reviewers line". A message string is code, so this delta, the BUGLOG release-note row and the plan's status rows get a full-scope re-check, and the plan's post-gate section a wording pass.
