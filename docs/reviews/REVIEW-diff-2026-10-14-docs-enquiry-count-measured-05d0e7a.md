# Review trail: enquiry count, measured results, branch docs/enquiry-count-measured

DIFF gate. **Depth: Normal**: it edits `new-website/SKILL.md` (an instruction file) and the plan.

**Verdict: gate passed.** 2 rounds, 12 findings (0 BUG, 2 RISK, 10 NIT): 10 fixed, 2 refuted. Round 2's two NITs were fixed after the last round and read by the prose-only re-gate.

## Rounds

| Round | Head | Reviewers | BUG / RISK / NIT | Outcome |
|---|---|---|---|---|
| 1 | 05d0e7a | codex 183 s 76k tok; melious glm-5.3 215 s 15k tok; fresh-eyes (sonnet) 137 s 117k tok | 0 / 2 / 8 | the fixes add owner advice; round 2 owed |
| 2 | 5d67553 (verify 05d0e7a..5d67553) | codex (medium) 73 s 43k tok; melious glm-5.3 132 s 13k tok | 0 / 0 / 2 | clean by (a2); NITs fixed without another round |

## Findings

| Id | Sev | Source | Round | Location | Finding | Status | Evidence |
|---|---|---|---|---|---|---|---|
| M1 | RISK | fresh-eyes | 1 | Q5, README, plan | A just-added site drops events for its first minute or so (seen once: four events answered 202, not stored); the new "look under Today" advice does not cover it. | fixed, locally_verified | `gate_keeper.ex` v3.2.1: `@policy_for_non_existing_sites :not_found` ("site not found in cache"); plan line added; Q5 and README say to tap again a few minutes later |
| M2 | RISK | codex | 1 | Q5, README | "views end yesterday" stated for every version from one measurement | fixed, locally_verified | qualified to "since Plausible 3.0"; v3.0.0 changelog (2025-04-11): "Last `7d` and `30d` periods do not include today anymore"; both v3.2.1 date paths end yesterday (`query_builder.ex` and `legacy_query_builder.ex`, `Date.shift(day: -1)`) |
| M3 | NIT | fresh-eyes | 1 | plan | "drops events only for bot, spam, IP and blocklist reasons" is wrong: `:not_found`, `:invalid` and others too | fixed | now "never drops an event for a missing goal" |
| M4 | NIT | fresh-eyes | 1 | plan, BUGLOG | cites only the newer date path | fixed | both paths and the changelog line cited |
| M5 | NIT | fresh-eyes, melious | 1 | Q5, README | 91-day view missing | fixed | "Last 7, 28, 30 and 91 days" |
| M6 | NIT | fresh-eyes | 1 | Q5 | self-hosted aside belongs in the plan, not an agent-loaded skill | fixed | removed from Q5; kept in the plan |
| M7 | NIT | melious | 1 | Q5, README, BUGLOG | "Today" and "Realtime" labels unconfirmed | fixed | `query-time-periods.ts` v3.2.1: `['Today', 'D']`, `['Realtime', 'R']`, `'Last 28 days'` |
| M8 | NIT | melious | 1 | BUGLOG | blocker state of the Firefox run unrecorded | fixed | row says none was turned on and the state was not recorded |
| M9 | NIT | fresh-eyes | 1 | plan row 8 | counts differ between row 7 (four) and the original BUGLOG row (three) | refuted | both internally consistent; row 8 counts against row 7's four |
| M10 | NIT | melious | 1 | `event_goal_join` not quoted in the brief | refuted | quoted in the round 2 brief; fresh-eyes read it at v3.2.1 and found no creation-time condition |
| N1 | NIT | melious | 2 | Q5, README, plan, BUGLOG | "since Plausible 3.0" stretches the changelog line, which names only 7d and 30d | fixed | owner text now says "checked in version 3.2.1"; the plan ties 28d and 91d to the v3.2.1 code |
| N2 | NIT | melious | 2 | BUGLOG | the blocker sentence reads as self-contradicting | fixed | "no blocker extension was used in any run, and whether Firefox's own tracking protection was on in the Playwright run was not recorded" |
