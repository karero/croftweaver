# DIFF gate: fix/ai-crawl-control-seen

Depth: Normal (a SKILL.md bullet agents load). Seats: Codex + GLM 5.3 on melious
(`SECOND_SEAT=melious`), fresh-eyes on Claude Sonnet in round 1. Gate id 20261112T102644Z-58309.
What changed and why: the AI crawlers bullet in `skills/search-console-setup/SKILL.md`, step 4,
said the Cloudflare check's own requests "may" show in AI Crawl Control. On 2026-11-12 one run of
the check's AI item against a free-plan domain showed every one of them counted within about
three minutes, and the Metrics tab there offered more than the 24 hours Cloudflare's page names.
Plan: none; a wording fix from a dashboard look (`SKILL-PLAN-ai-crawler-watch.md` listed it as not
checked).

## Round 1 (diff at cbf261df, base 25af21fc)

`reviewers: codex OK, melious OK`. `timings: codex 80s (28372 tokens), melious 67s (5549
tokens)`; fresh-eyes 17 s, 89,064 tokens. Evidence: Cloudflare's get-started page as fetched on
2026-11-12, the dashboard record before and after the run, and the check's crawler list.
`make check` exit 0 before the round.

| Id | Sev | Source | Where | Finding | Status | Fix / reason |
|---|---|---|---|---|---|---|
| E1 | BUG | fresh-eyes; melious (NIT) | "it showed the past 7 days" | One look at a 7-day view with data from 6 November does not show the tab holds 7 days | fixed | "it offered longer ranges too and showed several days of data" |
| E2 | RISK | fresh-eyes | Overview vs Metrics | The bullet sends the owner to Overview, the range sentences are about Metrics; which range to trust is unclear | fixed | "pick the longest date range on offer" (both tabs have a range picker, seen 2026-11-12) |
| E3 | RISK | codex; fresh-eyes; melious (NIT) | "leave the minutes after a check run out" | The record measures when counts appeared, not when Cloudflare files them; dropping a window can drop real visits; "the Cloudflare check" is not explained | fixed | Names the script; "each run sends your home page one request per AI crawler name … Take those off before you count crawler visits" |
| E4 | RISK | fresh-eyes | 24 hours vs 7 days | The owner can't tell which to believe | fixed | Same fix as E2: the bullet now says what to do, pick the longest range |
| E5 | NIT | fresh-eyes | "let through" | Not the dashboard's word | refuted | Unchanged line outside this diff; chosen in the earlier PLAN gate (F4) because the record showed allowed requests only |
| E6 | NIT | fresh-eyes | "(free, on Cloudflare)" | "free" used two ways | refuted | Unchanged heading outside this diff |

Codex also listed as unverifiable, not as findings: the dashboard behaviour itself (it has no
access to the dashboard; the record is the evidence) and the definition of a "request" in
Cloudflare's metric.

## Round 2 (verification, diff at f9c15e56)

`reviewers: codex OK, melious OK`. `timings: codex 65s (28572 tokens), melious 248s (14589
tokens)`. Both seats: E1, E2, E4 fixed as claimed; E5 and E6 rightly left (outside the diff). E3
partly fixed; its replacement drew F7 and F8.

| Id | Sev | Source | Where | Finding | Status | Fix / reason |
|---|---|---|---|---|---|---|
| F7 | BUG | codex | "each run sends your home page one request per AI crawler name" | A run with `--only` that leaves out the AI item sends no crawler requests | fixed | "each time it checks the AI crawlers (a full run does)"; `observe()` asks every request when `--only` is not given (`cloudflare-check.mjs`, `asked = only ? … : null`) |
| F8 | RISK | melious | "Take those off" | The owner can't subtract without knowing when the check ran | fixed | "Note when you run it, and take one request per name off the counts for each such run" |
| F9 | RISK | melious | "pick the longest date range on offer" | The longest range may hold little data, and the edit dropped the hedge on the Overview's reach | refuted | A longer range covers every shorter one's period, so picking it can't show fewer visits than a shorter one; the bullet makes no claim about how far back data reaches |
