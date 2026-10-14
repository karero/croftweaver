# Review trail: requirements for the weekly fix proposal

Artifact: `docs/reviews/SKILL-PLAN-scheduled-search-fixes.md` (PR #286). Gate: Normal, PLAN
(a plan, so never Light). Reviewers: Codex and GLM 5.3 on melious (`SECOND_SEAT=melious`).

## Round 1 — reviewed at ac8b71b, 2026-10-14

Codex 7 findings, GLM 8; overlapping pairs are listed once. 15 findings: 3 BUG, 8 RISK,
4 NIT. All fixed.

| # | Seat | Kind | Finding | Disposition |
|---|---|---|---|---|
| 1 | Codex, GLM | BUG + RISK | The window in R1 and the scenarios is neither shipped window: the text tracker ends 2 days back, the report page uses four full weeks to the last Sunday Google marks complete; a fixed 3-day lag was assumed | Fixed: R1 names the report page's window for the proposal, its figures and the measuring; scenario dates moved to it (checked against `search_report.py`) |
| 2 | Codex | RISK | T2 is page-level: it has no query for the cool-off and measuring, and the page total includes brand searches | Fixed: T2 counts the page's non-brand queries (`--page`); the cool-off is keyed by page for T2 |
| 3 | GLM, Codex | BUG + RISK | T2's check was not element-specific (an own title would allow a description rewrite), and showing the page's own text does not prove a snippet problem | Fixed: a new title only if Google shows the page's own title, a new description only if it shows the page's own description, and only if the assistant can say what is weak; scenario 3 no longer claims a new description "would not be shown" |
| 4 | Codex, GLM | RISK | R6 promised Windows; `_history.py` imports `fcntl`, which Windows Python lacks | Fixed: native Windows said not covered; WSL2 named as the README's path, untried here |
| 5 | Codex | RISK | The control comparison had no outcome when untouched pages are too few | Fixed: control defined (pages whose files did not change across both windows), with a "too little to compare against" outcome; scenario 8 shows both |
| 6 | Codex | RISK | The competitor comparison lacked a pinned source | Fixed: permalink to commit 2588c271; the recipe's own words quoted; the claim narrowed to "whatever checks the repository already has" |
| 7 | Codex | BUG | "CI on every pull request" is false: `ci.yml` skips documentation-only changes; "13 files" is today's count | Fixed: both reworded |
| 8 | GLM | RISK | Serper's price was relayed, not checked | Fixed: 2,500 free searches read on https://serper.dev on 2026-10-14; the per-1,000 price dropped |
| 9 | GLM | NIT | Scenario 8 reused scenario 1's figures for a different window | Fixed: own before-window figures |
| 10 | GLM | NIT | A page merged but not yet live fell between the exclusions | Fixed: named in R1's list |
| 11 | GLM | NIT | Scenario 2 gave one of T1's conditions only | Fixed |
| 12 | GLM | NIT | "Bing alone (a six-month total)" unexplained | Fixed |

Not acted on, as UNVERIFIABLE notes rather than findings: Google's server-side behaviour
(attribution, 7-day token; the token is tracked in #290), Bing's period, GitHub's 60-day
rule (in "Later", marked to recheck), and the owner's chat decisions.
