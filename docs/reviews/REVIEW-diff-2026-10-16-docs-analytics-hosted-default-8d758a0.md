# Review: new-website Q5, hosted Plausible first, no custom events at Cloudflare

Branch `docs/analytics-hosted-default`, commits d3921f04 (change) and 8d758a0e (round 1 fixes).
Gate: DIFF, Normal depth (`SKILL.md` is an instruction file agents load). Reviewers: Codex and
GLM 5.3 on melious; fresh-eyes (Sonnet) in round 1. 2 rounds, 12 findings, no BUG.

The owner's point, which the change carries: most site owners have no server for Plausible, so
they take the hosted version (from €9/mo) or rely on Cloudflare's counts; Cloudflare has no custom
events, so the enquiry count needs Plausible. Fact checked: Cloudflare's Web Analytics FAQ answers
"Does Web Analytics support custom events?" with "Not yet, but we may add support for this in the
future." (https://developers.cloudflare.com/web-analytics/faq/, read 2026-10-16).

| # | Sev | Seat | Round | Finding | Outcome |
|---|---|---|---|---|---|
| A1 | RISK | fresh-eyes | 1 | "counts no events, so it cannot show enquiries" too strong | fixed, externally verified (r2): "counts requests and visitors, not events such as an enquiry" |
| A2 | RISK | fresh-eyes, codex | 1 | cloud is now the default; dashboard facts and server mode checked on self-hosted only | fixed, externally verified (r2): "checked on self-hosted version 3.2.1; the cloud version may differ"; server mode keeps "not tried there with a real site" |
| A3 | RISK | fresh-eyes; NIT melious | 1 | "Most owners have no server" is a guess where the agent can ask | fixed, externally verified (r2): the agent asks the owner |
| A4 | NIT | fresh-eyes | 1 | grammar of the Web Analytics sentence | fixed, externally verified (r2) |
| A5 | NIT | fresh-eyes, melious | 1 | "the enquiry count below" vague, repeats | fixed, externally verified (r2): names the "Email Tap" paragraph |
| A6 | NIT | fresh-eyes, melious | 1 | line length; "most owners will use" unneeded | fixed, externally verified (r2): line reverted, dashboard line rewrapped |
| A7 | NIT | melious | 1 | quoted "not yet" must match the FAQ | fixed, externally verified (r2): quoted as "Not yet", checked against the live page |
| A8 | NIT | fresh-eyes | 1 | other files lead with self-hosted | partly fixed: `config.ts` comment names the cloud first. Not changed: the privacy page's CHOOSE ONE slot (neutral order) and the starter README (another open branch edits that paragraph) |
| B1 | RISK | codex; NIT melious | 2 | "the usual case" keeps the prevalence claim | refuted: it is the owner's own statement, which this change exists to record; the recommendation itself follows the owner's answer |

Round 2 found no BUG, so the rounds end. Not done: the starter README still says "(checked in
version 3.2.1)" without "self-hosted"; it is left for the open branch that edits that paragraph.
Merge note: another branch adds a links paragraph just above the rewritten Plausible sentence;
whichever lands second rebases and keeps both.
