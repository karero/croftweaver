# PLAN gate: SKILL-PLAN-ai-crawler-watch.md

Depth: Normal (a plan; it changes what a script does). Seats: Codex + GLM 5.3 on melious
(`SECOND_SEAT=melious`), fresh-eyes on Claude Sonnet in round 1. No red team: nothing touches
the server, user data, logins, money or deletion. Gate id 20261110T065051Z-23922.

## Round 1 (plan at 5a398bd8)

`reviewers: codex OK, melious OK`. `timings: codex 180s (74849 tokens), melious 166s (16781
tokens)`; fresh-eyes 54 s, 104,723 tokens. Evidence file: five READs (Cloudflare's and
Anthropic's pages, the maintainer's dashboard record, the guide page, the repo-wide count
search), sent as `--evidence`.

| Id | Sev | Source | Where | Finding | Status | Fix / reason |
|---|---|---|---|---|---|---|
| F1 | BUG | codex | Cost and risk | A wrong user-agent string can also cause a false `look`, not only miss a block | fixed | Names both ways |
| F2 | RISK | codex | bullet 1 | "7-day view showed data" reads as a 7-day promise; the record shows data in a 7-day range, not 7 days of data | fixed | Bullet names no range: "look in the first days after launch" |
| F3 | RISK | codex | How it is tested | `check_clean.sh` credited with checking wording | fixed | Credited with private names, contact details and credentials only |
| F4 | RISK | melious | bullet 1 | The record shows allowed requests only; blocked visits may not show | fixed | "requests … Cloudflare let through"; blocked requests in the not-checked list |
| F5 | RISK | melious | Follow-on text | Two lines claimed as the only "six", not searched | fixed | Repo-wide search in evidence READ 5; the build reruns it |
| F6 | RISK | fresh-eyes | bullet 2 | "not a sign that something is broken" goes beyond "no published measurement" | fixed | "a week of silence tells you little either way" |
| F7 | RISK | fresh-eyes | bullet 2 | The link's promised content (Google ranges, existing-site measurements) not evidenced | fixed | READ 4b quotes both from the live page |
| F8 | RISK | fresh-eyes | bullet 1 | "seven" in a shipped skill goes stale on the next list change | fixed | "the Cloudflare check's own crawler-named requests" |
| F9 | NIT | melious, fresh-eyes | bullet 1 | A dated one-zone observation in a shipped skill | fixed | Removed from the bullet; kept in the plan's sources |
| F10 | NIT | melious | bullet 1 | Cloudflare's table lists a 24-hour window under all plans | refuted | The bullet quotes the page's own sentence, "on free plans, the Metrics tab only displays metrics for the past 24 hours" (READ 1); it says nothing about paid plans |
| F11 | NIT | fresh-eyes | bullet 1 | Overview (7 days seen) and Metrics (24 hours) read as a contradiction | fixed | Bullet names the Metrics tab for the 24 hours and says the Overview's reach is unchecked |
| F12 | NIT | fresh-eyes, melious | How, idea 6 | The `1.0` and missing `+URL` are invented | fixed | Plan says so, as a reason for the "hint" wording |
| F13 | NIT | melious | Not checked | Whether the check's requests show in AI Crawl Control could be settled with one run | open | Offered to the maintainer with the go; the bullet keeps "may" |

## Round 2 (verification, plan at d6d19aa3)

`reviewers: codex OK, melious OK`. `timings: codex 207s (72489 tokens), melious 317s (26741
tokens)`. Both seats: F1–F9, F11, F12 fixed as claimed; F10's refutation accepted; F13 left
open as its row says. No BUG.

| Id | Sev | Source | Where | Finding | Status | Fix / reason |
|---|---|---|---|---|---|---|
| F14 | RISK | codex | bullet 2 | "tells you little either way" still claims more than "no published measurement" (F6 residue) | fixed | "So there is no yardstick for a new site's first weeks. Check that the crawlers come" |
| F15 | RISK | melious | Follow-on text | The count search misses a count worded without "crawler"/"request", and lists of the names | fixed | Second search for the names listed together and for Amazonbot (READ 6); the plan now says what the searches can miss |
| F16 | RISK | melious | bullet 2 | No support that `search-console-insights` reads Google's and Bing's AI reports | fixed | Support added: `references/ai-reports.md` (READ 7) |
| F17 | NIT | melious | bullet 1 | Filters shown as usable, though none was applied | fixed | "offers Hostname and Path filters"; sources say none was applied |
| F18 | NIT | melious | bullet 1 | "is not shown" is stronger than "identifies … by user agent strings" | fixed | "isn't counted as an AI crawler" |
| F19 | NIT | melious | bullet 2 | Attribution of the ranges to Google assumed | fixed | "The ranges Google gives"; READ 4c shows the page's heading "Google, in its own words" |

## Round 3 (verification, plan at c4717d7e)

`reviewers: codex OK, melious OK`. `timings: codex 188s (52176 tokens), melious 195s (20953
tokens)`. F14–F19 accepted as fixed by both seats except F14 (codex, below). No BUG in three
rounds, so the rounds end here; one wording pass follows.

| Id | Sev | Source | Where | Finding | Status | Fix / reason |
|---|---|---|---|---|---|---|
| F20 | RISK | codex | bullet 2 | "no yardstick" still goes beyond "we found no published measurement" (F14 residue) | fixed | Sentence cut; the bullet now goes straight to "Check that the crawlers come" |
| F21 | RISK | codex | New test | A substring stub passes a wrong token such as `NotClaude-SearchBot/1.0` (reproduced with Node) | fixed | The stub records user agents; the test also asserts one equals the row's whole string |
| F22 | RISK | melious | Follow-on text | "The build runs both again" names no wiring | fixed | Stated as a manual build step, and added to the Status table's build row |
| F23 | NIT | melious | New test | `Claude-SearchBot (403)` detail format assumed | fixed | Plan cites the code's form `${c.name} (${c.status})` (`cloudflare-check.mjs:1065`) and the ClaudeBot test's assertion (`cloudflare-check.test.mjs:615`) |
| F24 | NIT | melious | evidence READ 3 | The record's 415 requests don't add up to the per-company sum (332) | follow-up | No plan claim rests on either number; the record is the maintainer's |
| F25 | NIT | melious | BUGLOG row | "seven names" goes stale | fixed | "Claude-SearchBot added to the check's crawler names" |

## Wording pass (round 3's changes, `--diff --base c4717d7e`, plan at 885a8d98)

`timings: codex 80s (45032 tokens), melious 266s (20084 tokens)`. Codex: "No BUG/RISK/NIT
findings", and it verified the detail format against the code.

| Id | Sev | Source | Where | Finding | Status | Fix / reason |
|---|---|---|---|---|---|---|
| F26 | RISK | melious | New test | The `${c.name} (${c.status})` form and the ClaudeBot test's assertion are not shown | refuted | `cloudflare-check.mjs:1065`: `.map((c) => \`${c.name} (${c.status})\`)`; `cloudflare-check.test.mjs:615`: `assert.match(r.by.ai.detail, /ClaudeBot \(403\)/);` (the seat has no file access; Codex read both) |
| — | (claim) | melious | Follow-on text | Whether Amazonbot appears outside the check | checked | `git grep -n Amazonbot` outside `docs/reviews/`: the script's line 44 and a test fixture only |

## Close

No BUG open. Three rounds and a wording pass; 26 findings: 22 fixed, 2 refuted, 1 follow-up (F24),
1 NIT open for the maintainer (F13). Gate total 433,828 tokens logged (nine seat runs, fresh-eyes
included).
