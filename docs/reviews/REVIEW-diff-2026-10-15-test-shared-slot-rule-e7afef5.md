# DIFF review — test/shared-slot-rule — one slot rule and one allowlist for placeholders.spec.ts and privacy-host.spec.ts
Base `bfe7c55` (PR #332's head), rebased onto main `e4972c5` once #332 merged, patch unchanged · depth: Light, moved to Normal (a BUG in Light's extra round) · verdict: CLEAN (Light 2 rounds, Normal 2 rounds; 15 findings, 2 BUG fixed) · authority used: BRANCH-COMMIT and WORKTREE-WRITE — atom B (the owner, in chat: "yes to: Should I make that fix on this branch and run the review again?"); the branch and worktree were made by the session "Share one slot pattern between two starter specs", which no longer exists

Seats: Light: Codex alone (medium). Normal: Codex (config effort in round 1, medium in round 2), GLM 5.3 on melious, a fresh-eyes sub-agent (Sonnet) in round 1.

| Round | Head | Artifact | BUG/RISK/NIT | Seats |
|---|---|---|---|---|
| Light 1 | `2e8b0a6` | full | 1/0/0 | codex 74 s / 40,480 |
| Light 2 | `56a117e` | delta | 1/0/0 | codex 73 s / 37,748 |
| Normal 1 | `e7afef5` | full | 2 (refuted)/4/5 | codex 230 s / 67,849; melious 295 s / 26,264; fresh-eyes 73 s / 66,145 |
| Normal 2 | `87ac93a` | delta | 0/0/2 | codex 100 s / 83,610 (none); melious 201 s / 17,412 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| L1 | BUG | codex | Light 1 | The "unreported" guard could not fire, and a slot in the placeholders ALLOWLIST or inside an exempt element was skipped by privacy-host and passed by placeholders | fixed (`56a117e`), externally_reverified in part (Light 2 found L2) | allowlist and exempt selector moved to `_helpers.ts` (`PLACEHOLDER_ALLOWLIST`, `PLACEHOLDER_EXEMPT`); dead guard removed |
| L2 | BUG | codex | Light 2 | An exempt element inside the mark (`<span data-analytics-host><code>[…]</code></span>`) was still skipped | fixed by a cut (`e7afef5`), externally_reverified (N1, N2) | skip only a plain mark: text alone, no exempt ancestor; five wrappers tested; a mutation dropping the child check fails the page test |
| N1 | RISK | codex | Normal 1 | A mark in a shadow root is found by Playwright, not read by placeholders | fixed (`87ac93a`), externally_reverified | `getRootNode() === document`; shadow-root page case; mutation fails it |
| N2 | RISK | fresh-eyes | Normal 1 | `innerText` applies text-transform, placeholders reads text nodes | refuted as a skip path; changed to `textContent` anyway | Chromium: capitalize gives `[A ANALYTICS.ScriptHost]`, uppercase `[A ANALYTICS.SCRIPTHOST]`; the case-sensitive name check fails, so the mark is compared |
| N3 | RISK | fresh-eyes | Normal 1 | An allowlist entry running on into the slot (`[Note [A ANALYTICS.scriptHost]`) passed placeholders while privacy-host skipped | fixed, externally_reverified | `inAllowlist` refuses when any entry contains the slot; unit test; mutation fails it |
| N4 | NIT | fresh-eyes | Normal 1 | `innerText` is undefined inside `<svg>` | fixed by `textContent` | |
| N5 | NIT | fresh-eyes | Normal 1 | The ALLOWLIST rename loses a site's own entries on update | fixed, externally_reverified | note in `placeholders.spec.ts` |
| N6 | NIT | fresh-eyes | Normal 1 | The exported `/gu` regex is stateful under `.test()` | no change: the comment already warns | reviewer's own second option |
| N7, N8 | BUG | melious | Normal 1 | `hostOf`'s catch returns null, so two tests fail | refuted, re-checked by codex | the catch returns the text; the tests pass when run |
| N9 | RISK | melious | Normal 1 | Same premise | refuted | same |
| N10 | NIT | melious | Normal 1 | `hostOf` defaulted to skipping | fixed, externally_reverified | default `plain = false` |
| N11 | NIT | melious | Normal 1 | `_helpers.ts` comment under-described the skip | fixed, externally_reverified | |
| N12 | NIT | melious | Normal 2 | "Until 2026-10" may be the wrong date | refuted | this branch makes the rename, 2026-10-15 |
| N13 | NIT | melious | Normal 2 | A 138-column comment line | fixed (`3506239`), locally_verified; closing edit not externally re-verified | |

Notes: Normal round 2 had no BUG and no RISK (stop condition a2). No substantive BUG in the Normal gate, so no wording pass. Tests on every head: the starter's `npm test` 73 passed, 1 skipped (the unfilled positioning spine, as on main); `npm run check` 0 errors. After the rebase onto main `e4972c5` (which brought #336): the same 73 passed, 1 skipped; `npm run check` 0 errors.
