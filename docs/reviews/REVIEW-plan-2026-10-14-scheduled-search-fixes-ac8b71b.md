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

## Round 2 — verification at e655788, 2026-10-14

Codex and GLM 5.3. The melious seat timed out at 300 s (`MELIOUS_API_TIMEOUT=300`); GLM 5.3
on ollama stood in. Codex 5 findings, GLM 8; overlapping ones are listed once. 11
findings: 1 BUG, 7 RISK, 3 NIT. GLM reported 12 of round 1's 15 verified fixed; rows 1 to
3 below are the partial ones.

| # | Seat | Kind | Finding | Disposition |
|---|---|---|---|---|
| 1 | GLM | BUG | R4 still said CI runs "on each pull request", against the round-1 fix | Fixed: "each pull request that changes the site" |
| 2 | Codex, GLM | RISK | T2 named no query for the live check, no position aggregation, and R3 still kept a query | Fixed: the live check searches the page's strongest non-brand query; position is the impression-weighted average of its non-brand queries; T2 measuring uses the page's non-brand totals; R3 keeps a query for T1 only |
| 3 | Codex | RISK | The competitor claim still lacked support | Fixed in part: narrowed to "the recipe names no test suite of its own", which the pinned recipe shows. A copy in the repo was declined: the permalink is to a fixed commit |
| 4 | Codex | RISK | "2,500 searches free" lacked dated evidence | Refuted: R4 cites https://serper.dev, read 2026-10-14 |
| 5 | Codex | RISK | The control ignored shared files (layouts, config) | Fixed: a change to anything pages share leaves no control |
| 6 | GLM | RISK | Drill-downs ran on another window than the figures they prove | Fixed: every drill-down behind a proposal uses the report page's window |
| 7 | GLM | RISK | The exclusions read the tracker's `~`, `≠`, `‡` marks from another window | Fixed: "under 10 non-brand impressions in the window"; the move marks dropped (proposals do not rest on moves) |
| 8 | GLM | RISK | Measuring set no completeness condition | Fixed: the comparison first appears in the report whose complete data reaches the second window's last Sunday |
| 9 | Codex, GLM | NIT | Cool-off wording still said "page and query" everywhere; an assistant's abstention was called a turn-down | Fixed: proposals identified by page and query (T1) or page (T2); an abstention is "set aside for 12 weeks like a turned-down one" |
| 10 | GLM | NIT | Scenario 3 did not say what happens to the title | Fixed: the title branch is stated |
| 11 | GLM | NIT | "Never sees two sets of numbers" was not true beside the tracker's tables | Fixed: the proposal names its window, the tracker's tables keep theirs |

## Round 3 — verification at aee1afe, 2026-10-14

Codex and GLM 5.3 on melious (`MELIOUS_API_TIMEOUT=600`). Both confirmed round 2's fixes
landed. Codex 3 findings, GLM 5; merged, 6 findings: 3 RISK, 3 NIT, no BUG.

| # | Seat | Kind | Finding | Disposition |
|---|---|---|---|---|
| 1 | Codex, GLM | RISK | Today's `gsc_query.py --page`/`--query` take a day count ending two days back, not dates, so "drill-downs on the report window" cannot run on them | Fixed: R1 says so and points the build at `search_report.py`, which already drills down on the report window; scenario 1 and the T1/T2 rows no longer name the CLI flags |
| 2 | Codex, GLM | RISK | The competitor claim still rests on a document outside the repo | Fixed in part: the sentence now says the recipe was read in full at that commit on 2026-10-14. A copy in this public repo was declined again: it is another project's file, and the permalink cannot change. Left for the owner to overrule |
| 3 | Codex | RISK | The Serper allowance is still asserted (refuted in round 2) | Fixed rather than argued: dated as read, with "check the current allowance"; scenario 3 drops the number |
| 4 | GLM | NIT | The status row's round-2 tally did not match the trail's raw entries | The row counts findings after merging duplicates between seats (13 raw, 11 merged); it now says so |
| 5 | GLM | NIT | An abstention's 12 weeks had no start and the report did not say until when | Fixed: "12 weeks from that report", and the report says until when |
| 6 | GLM | NIT | R1 said the measuring uses the proposal window, against R3's live-date windows | Fixed: same rule, anchored on the live date |

Round 3 had no BUG, so the cross-model rounds end here; one wording pass follows.
