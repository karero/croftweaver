# DIFF gate: feat/ai-crawler-watch

Depth: Normal. Seats: Codex + GLM 5.3 on melious (`SECOND_SEAT=melious`), fresh-eyes on Claude
Sonnet in round 1. Plan: `SKILL-PLAN-ai-crawler-watch.md` (PLAN gate clean, trail
`REVIEW-plan-2026-11-10-ai-crawler-watch.md`). Gate id 20261110T084708Z-25496.

## Round 1 (diff at de375c4b, base 9f7d3ff6)

`reviewers: codex OK, melious OK`. `timings: codex 90s (33852 tokens), melious 267s (19196
tokens)`; fresh-eyes 44 s, 103,468 tokens. Evidence: the plan's READs, the two count searches
rerun (READ 8), the mutation check (READ 9: the new test fails with the row deleted or its string
changed) and the repo checks (READ 10: `make test-cloudflare-check` 464 pass, 0 fail, 0 skipped;
`make check` exit 0). Codex: "No BUG/RISK/NIT findings". After the round, main had moved (#514,
#515, #516, none touching these files except `docs/BUGLOG.md`, not yet edited here), so the
branch was rebased onto it.

| Id | Sev | Source | Where | Finding | Status | Fix / reason |
|---|---|---|---|---|---|---|
| D1 | RISK | fresh-eyes | search-console-setup, AI crawlers bullet | The 24-hour limit is the Metrics tab's, but the bullet sends the owner to the Overview; a reader can't tell which tab the limit is for | fixed | **Metrics** in bold, "the Overview's own date ranges", and "again every few days" |
| D2 | NIT | fresh-eyes | same bullet | "the kit" is jargon to a site owner | fixed | "we haven't checked", as the next bullet says "we found" |
| D3 | NIT | melious | same bullet | "how far back the longer ranges reach" understates the 7-day view seen | refuted | The record shows the 7-day view had data, not that it reaches back 7 days (PLAN gate F2); "own date ranges" now says what is unchecked |
| D4 | NIT | melious | How long bullet | "We found no published measurement" is a negative universal with no date | fixed | "when we last checked, in November 2026" (the guide: "Checked on 3 November 2026", READ 4) |
| D5 | NIT | melious | CLOUDFLARE_CHECK.md | The numeral "seven" goes stale on the next list change and no test pins it | fixed | Both lines word it without a number |
| D6 | NIT | melious, fresh-eyes | cloudflare-check.mjs, new row | The user-agent string is made up from the token; nothing says so | fixed | One-line comment above the row |
