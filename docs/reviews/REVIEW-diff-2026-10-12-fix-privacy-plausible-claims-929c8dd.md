# DIFF review — fix/privacy-plausible-claims — template: per-site Plausible script, privacy pages (EN, DE) say what the script does, the analytics gate test

Base `896e3c5` (origin/main) · depth: **High** (privacy and legal text; a test that guards what visitors are told) · verdict: **OPEN** — round 7 found 3 BUGs, fixed in `7845b8d` and not re-verified; one RISK waits for the owner (instance facts) · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session created the worktree and the branch); POST AUTHORITY — atom A (this session opens the PR). GATED-THIS-DIFF is not claimed: no consolidated marker is stamped.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT (both seats, before dedup) |
|---|---|---|---|---|---|
| 1 | `929c8dd` | full `origin/main...929c8dd` | codex-cli 0.162.1, gpt-6.1-sol, high, read-only; ollama-cloud glm-5.3 (melious FAILED: quota); fresh-eyes (Sonnet sub-agent) | codex 403 s / 72,052; glm 830 s | 2 / 6 / 2 |
| 2 | `452e438` | delta since `929c8dd` | codex, glm, fresh-eyes | codex 603 s / 97,842; glm 711 s | 2 / 5 / 5 |
| 3 | `640327f` | delta since `452e438` | codex, glm, fresh-eyes | codex 731 s / 93,006; glm 429 s | 2 / 3 / 6 |
| 4 | `1d5ce41` | delta since `640327f` | codex, glm, fresh-eyes | codex 823 s / 105,297; glm 671 s | 4 / 4 / 6 |
| 5 | `fdda26f` | delta since `1d5ce41` | codex only (`--seat codex`), high | codex 610 s / 102,361 | 4 / 1 / 0 |
| 6 | `9e5c34c` | delta since `fdda26f` | codex only, high | codex 506 s / 79,690 | 2 / 2 / 0 |
| 7 | `c45689f` | delta since `9e5c34c` | codex only, high | codex 457 s / 67,257 | 3 / 0 / 0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| T1 | BUG | codex | 1 | the stub check accepts `plausible.init()` anywhere (prose, JSON, an undefined initializer) | fixed `452e438`; externally_reverified r2 | stub read only inside inline script tags, then run in a bare VM (rounds 2–6 extend it) |
| T2 | BUG | codex | 1 | header says the vendor's legal assessment "does not address access"; it addresses access by denying storage | fixed `452e438` | header comment names what the assessment covers and what it does not |
| T3 | RISK | codex, glm | 1 | behaviour claims (foreground time, location, daily counting, IP) lack support | fixed `452e438`, `640327f` | sentences now follow the script's own source and the vendor policy; the storage period is a slot, not a claim |
| T4 | RISK | codex | 1 | `plausible.init ();` and `plausible.init({})` read as no stub | fixed `452e438` | whitespace and arguments accepted; fixtures `spaced`, `options` |
| T5 | RISK | codex, glm | 1 | privacy text omits the opt-out flag read and the automation check | fixed `452e438` | both pages say both reads and that neither is sent |
| T6 | RISK | codex | 1 | "GDPR-clean" in WEBSITE_ARCHITECTURE | fixed `452e438` | phrase removed |
| T7 | RISK | glm | 1 | "No data is passed on to third parties" had no support | fixed `452e438` | sentence cut; the processor slot carries the point |
| T8 | BUG, RISK | codex, glm | 2 | a commented-out or quoted `plausible.init()` counts as a stub; the CSP check accepted `host.evil.invalid` | fixed `640327f` | stub executed with a spy; CSP tokens compared whole |
| T9 | RISK | codex, glm | 2–3 | scroll/engagement and "stored with" claims unsupported; the optional-measurement sentence fits only all-on or all-off | fixed `640327f`, `ffaaa54`, `1d5ce41` | one slot sentence per measurement; stored list follows the vendor policy wording |
| T10 | BUG | codex | 3 | execution checked on `index.html` only; a fake init passes (`fakeinit`) | fixed `ffaaa54` | every page's stub runs; init spy; fixtures |
| T11 | RISK | codex | 3 | CSP reader accepts unrelated nonce or hash, `script-src-elem 'none'`, duplicates | fixed `ffaaa54`, `fdda26f` | first directive wins, `script-src-elem` governs; 16 policy fixtures |
| T12 | BUG | codex | 4 | empty `script-src-elem;`; substring matches (`'unsafe-inline'junk`); `strict-dynamic` never rejected; unseeded run never calls init | fixed `fdda26f` | whole tokens; presence kept apart from tokens; second run with nothing installed; fixtures `branchy`, `p_junk`, `p_emptyel`, `p_strict` |
| T13 | RISK | codex | 4 | CSP judged against the home page's stub only | fixed `fdda26f` | every distinct stub of the live build |
| T14 | BUG | codex | 5 | replacement init passes without the seed spy; init defined before plausible fails; checksum de-duplication skips distinct stubs; comment removal alters JS strings | fixed `9e5c34c` | fixtures `replaced`, `preassign`, `commentstr`; `cmp -s` |
| T15 | BUG | codex | 6 | `<script-x>` keeps a comment alive; Proxy invariant error on non-configurable init; new wrapper per read | fixed `c45689f`; reverified r7 only in part | fixtures `scriptx`, `identity`, `defprop`, `quotedtag`, `alias`; fail on the old code (checked) |
| T16 | BUG | codex | 7 | an own accessor makes `'init' in plausible` true early; a captured alias of init is not counted; inherited init was shadowed | fixed `7845b8d` for the inherited init (fixture `inherit`); the other two named in the header as unsupported shapes (the gate may reject such a stub) | not re-verified externally |
| T17 | RISK | codex | 4–7 | "sends and stores" for outbound and download addresses assumes the instance keeps them | OPEN — owner; README now asks for one test click and a look at the report | no ingestion evidence from here |

Waivers: none. Deferrals: none. Follow-ups: the consent position (§ 25 TDDDG) is left to each site owner; the template header lists the sources and draws no conclusion.

Notes:
- High depth asks for the fresh-eyes seat and Codex at config effort every round. Rounds 5–7 ran Codex alone: the findings were confined to one test script, and the second seat (ollama stand-in) had hit quota limits. The script's "fewer than 2 reviewers" notice is expected there. Fresh-eyes findings of rounds 1–4 were triaged in the session and are folded into the rows above; their raw text is in the PR comment.
- Melious was out of credits in round 1; ollama-cloud with glm-5.3 stood in for the second seat.
- Seven rounds; each round after the third found a stub shape the gate mishandled, so the budget rule allowed another. The host stopped after round 7: the remaining shapes are unusual hand-written stubs that the gate rejects; no shape the reviewers found passes without a call to init. Run round 8 if the owner wants the last fixes read by a reviewer.
- Data check: no credentials; no private names in the diff or in the reviewer output (checked with the repo's clean script and a grep). Destinations: Codex and ollama-cloud, the repo's review convention; Melious (the owner's choice for the second seat) did not run.
- Checks on `c45689f`: `make check` passed; in the template, `npm run check` 0 errors, the gate (4 builds, 29 fixtures, 16 policies) passed, `npm test` 67 passed and 1 skipped. On `7845b8d`: the gate's self-test (30 fixtures) passed.
