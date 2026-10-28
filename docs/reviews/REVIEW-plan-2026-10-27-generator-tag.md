# PLAN review: a generator tag in every starter site

Plan: `docs/reviews/SKILL-PLAN-generator-tag.md`. Gate: independent-review PLAN, depth Normal.
melious failed every round (out of credit), so all four rounds ran on Codex alone (owner rule,
2026-10-26). No red team: the change touches no user data, login, money, deletion or schema.

| Round | Findings | Disposition |
|---|---|---|
| 1 | BUG: `whats-new.sh` does not track `Base.astro`/`config.ts`. RISK: the `PAGES` loop skips 404 and noindex pages. RISK: an existing site could gain the tag without being told | all fixed: no update route brings the tag; the test reads every built page; on request only, with the same message |
| 2 | RISK: a missing switch could fail `npm run check` | fixed: narrowed with `'GENERATOR_TAG' in config` |
| 3 | RISK: removing only the switch does not reproduce an existing site | fixed: the old-site check uses today's `Base.astro` and `config.ts` |
| 4 | none | clean (earned by: old-site-compat) |

Totals: 4 rounds, 5 findings (1 BUG, 4 RISK), all fixed. Codex tokens: 50,744; 48,450; 36,202; 44,169.
