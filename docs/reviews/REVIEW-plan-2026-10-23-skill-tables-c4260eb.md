# PLAN review — docs/reviews/PLAN-tables.md — a Tables section, the CSS and a test in the starter
Round 1 saw draft 1 at `c4260eb` · depth: Normal (tooling that ships to sites, no High-row item) · verdict: round 1 had a BUG, fixed in draft 2; round 2 (Codex alone) found no BUG and one RISK, recorded as a done-condition of build step 2. Final state: no BUG open. DEGRADED: Codex alone in every round (GLM 5.3 on melious.ai has no balance, the ollama seat is at its weekly limit; the owner's OK covered Codex only, quoted: "Yes, send the plan to Codex alone (this repo's content, no melious, no ollama)."). No red team: the plan touches no server, user data, logins, money, deletion or schema.

| Round | Head | Artifact | Reviewer | seconds / tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `c4260eb` | the whole plan (draft 1) | codex-cli gpt-6.1-sol, config effort, read-only | 473 s / 94,605 | 1 / 2 / 0 |
| 2 | `413c6e5` | the whole plan (draft 2), `--verify` | Codex medium, read-only | 83 s / 51,765 | 0 / 1 / 0 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| P1 | BUG | Codex | 1 | "a site can narrow `PAGES`" is no exemption: the sitemap and `llms.txt` checks reject a live route missing from it | fixed in draft 2 | `tests/seo.spec.ts` line 165 ("sitemap matches PAGES") and `tests/llms-coverage.spec.ts` lines 59 and 72 read; the plan now has a `TABLE_EXEMPT` list with reasons, a test that each entry is a live route, and says `PAGES` stays whole |
| P2 | RISK | Codex | 1 | the starter has no table, so `a11y.spec.ts` never audits table semantics or contrast | fixed in draft 2 | the contract layer runs axe on the fixtures (light and dark, 360 and 1280 px) and counts the roles in the browser's accessibility tree; Safari and VoiceOver stay unchecked |
| P3 | RISK | Codex | 1 | nothing shows that restoring `hyphens: auto` produces a detectable broken word | fixed in draft 2 | on the croftweaver site `hyphens: auto` alone was not caught while the column held the word; the plan's fixture forces a long word into a narrow column and requires the word-break assertion to fail, once on CI with a deliberate break |
| P5 | RISK | Codex | 2 | the claim that a narrow fixture makes Chromium hyphenate the word has no reproduced evidence for the fixture | fixed in draft 3 as a done-condition; the claim stays unproven until built | the plan's step 2 now needs two logs in the PR (baseline pass, and the single break failing at the word-break assertion) with the fixture's `lang`, dimensions and browser version; the croftweaver-site observation is quoted in the plan as the only evidence so far |
| P4 | — | author | 1 | the plan said a new spec "reaches existing sites through `whats-new`"; Codex's checked claims show it is reported for manual copying | fixed in draft 2 | `scripts/whats-new.sh` line 361 and the plan's step 4 reworded |

Notes: Codex also ran the skill-budget check, which stopped on a temporary-directory self-test; that is the sandbox, not the plan.
