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
