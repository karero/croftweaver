# DIFF review — test/privacy-host-matches-config — a starter test that the privacy page's analytics host is ANALYTICS.scriptHost's
Base `5d35db1` · depth: Normal (mostly test code, but it touches a comment in the shipped `src/config.ts`, markup in both privacy pages and a bullet in `website-qa/SKILL.md`; no visitor-facing word changes, so not High) · verdict: CLEAN (3 rounds and a wording pass; 12 findings, 1 BUG fixed) · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session created the worktree and the branch)

Seats: Codex (gpt-6.1-sol, codex-cli 0.162.1, read-only; config effort in round 1, medium after), GLM 5.3 on melious, a fresh-eyes sub-agent (Sonnet) in round 1.

| Round | Head | New findings (BUG/RISK/NIT) | Seats |
|---|---|---|---|
| 1 | `ab9f2f8` | 0/3/4 | codex 216 s / 69,695; melious 198 s / 7,386; fresh-eyes 93 s / 78,881 |
| 2 | `5913365` | 1/0/1 | codex 136 s / 48,288; melious 353 s / 14,659 |
| 3 | `464768c` | 0/2/1 | codex 101 s / 72,200 (none); melious 1048 s / 38,833 |
| wording pass | `7991261` | 0/0/0 | codex 33 s / 14,370 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | RISK | codex, melious, fresh-eyes | 1 | Regexes on the sentence's wording pass silently once it is reworded or translated | fixed, externally_reverified (r2) | `5913365`: both pages wrap the slot in `<span data-analytics-host>`; the test reads that element |
| F2 | RISK | fresh-eyes | 1 | `startsWith('[')` skipped a host left in brackets | fixed (see R2-1) | |
| F3 | RISK | melious | 1 | `new URL(scriptHost)` throws on a bare host | refuted, re-checked by codex r2 | `Base.astro:174` builds `${scriptHost}/js/${scriptId}.js`, so a bare host is already broken; the throw fails loudly |
| F4, F5 | NIT | melious, fresh-eyes | 1 | Punctuation, a phrase, two hosts or quotes beside the host gave a confusing failure | fixed, externally_reverified (r2) | the span holds the host alone |
| F6 | NIT | fresh-eyes | 1 | README file list and website-qa spec list left out the spec | fixed, externally_reverified (r2) | |
| F7 | NIT | fresh-eyes | 1 | The page notes did not name the test | fixed, externally_reverified (r2) | |
| R2-1 | BUG | codex (melious: RISK) | 2 | `/^\[\s*\p{Lu}/u` skipped `[Plausible.io]`, `[Wrong.example`, `[P]`, which `placeholders.spec.ts` does not report either | fixed, externally_reverified (r3) | `464768c`: a strict rule, skip only one whole bracket that starts with a capital and names `ANALYTICS.scriptHost`. Invariant: whatever is skipped matches `placeholders.spec.ts:36`. Variants in node: both shipped slots, `[A ANALYTICS.scriptHost]`, `[AANALYTICS.scriptHost]` skip and match it; `[ ANALYTICS.scriptHost]`, `[Plausible.io]`, `[P]` are compared |
| R2-2 | NIT | melious | 2 | A failure names near-correct text | fixed, externally_reverified (r3) | the message quotes the marked text |
| R3-1 | RISK | melious | 3 | `hostOf` may return null for unparseable non-slot text | refuted | null comes only from the `SLOT` test (line 23); the `catch` returns the text (line 27); codex r3 reproduced quoted failures for `[Wrong.example` and `[P]` |
| R3-2 | RISK | melious | 3 | The subset claim rests on a quoted rule the seat could not read | refuted | `placeholders.spec.ts:36` is `/\[\s*\p{Lu}\s*[^\]\s][^\]]*\]/gu`; codex r3 verified the subset against the file |
| R3-3 | NIT | melious | 3 | "(line breaks become spaces)" is an unchecked claim about innerText | fixed, externally_reverified (wording pass) | `7991261` |

Follow-ups: one slot pattern shared by `placeholders.spec.ts` and this spec in a plain helper module, so the two cannot drift (melious, rounds 2 and 3).
Notes: Tests on every head: the starter's `npm test` 71 passed, 1 skipped (the unfilled positioning spine, as on main), `npm run check` 0 errors. Mutations in a scratch state, then restored: `/privacy` filled with `plausible.io` fails, with `https://analytics.example.com/js/script.js` passes; a copied `/datenschutz` filled with `wrong.example` fails. `scripts/check_template_coverage.sh` and `scripts/check_clean.sh` (with the denylist) OK on a clean export of `7991261`; `scripts/check_skill_budgets.sh` OK. The branch started from #330's head and was rebased onto main once #330 merged, before round 1.
