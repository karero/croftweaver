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

## Round 2 (verification, diff at 48df96fe, base ae61aed8)

`reviewers: codex OK, melious OK`. `timings: codex 95s (42470 tokens), melious 436s (30322
tokens)`. Both seats: "No BUG/RISK/NIT findings"; D1, D2, D4, D5 and D6 fixed as claimed, D3's
refutation upheld. Checks before the round: the check's test file 103 pass, 0 fail, 0 skipped;
`make check` and `check_clean.sh` exit 0.

GLM noted three things outside the diff, none a finding here. (1) Cloudflare's page scopes the
24-hour Metrics limit to free plans in one sentence, but its table lists it under all plans. The
bullet quotes only the sentence, so it is accurate as written; re-read the page if the bullet is
rewritten. (2) Anthropic's page carries no calendar date. (3) The count search looked for "six",
not "seven"; the diff adds no numeral to prose.

The claims sweep (`sweep_claims.sh --base origin/main`) listed 11 sentences in the two prose
files. Each is one the round-2 seats checked against READs 1 to 4c and 7.

## Close

No BUG open. Two rounds, 6 findings: 5 fixed, 1 refuted. Round 2 had no findings, so no wording
pass follows. Gate total 229,308 tokens logged (five seat runs, fresh-eyes included). The
"Next release notes" row in `docs/BUGLOG.md` was written after the last round.
