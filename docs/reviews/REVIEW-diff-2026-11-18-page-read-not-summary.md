# Review trail: a web page's READ is the page, not a summary (2026-11-18)

Change: one sentence in `skills/independent-review/SKILL.md`, step 2's evidence rules. Gate
20261118T152142Z-82274, DIFF, Normal depth: an instruction file agents load is never Light
(REVIEW-RULES). Codex alone (REVIEW-RULES), plus one fresh-eyes pass (Opus subagent) at round 1.

Why: sessions sent a fetch agent's summary of a docs page as evidence, and Codex marked those
claims unverifiable (the plugin-directory options paper, two rounds on 2026-11-18).

Result: clean at round 3. 3 rounds, 5 findings (1 BUG, 2 RISK, 2 NIT), all fixed.

| Round | Seat | Finding | Disposition |
|---|---|---|---|
| 1 | Codex, fresh-eyes | RISK: "a fetch tool's answer is a summary" stated for every tool | fixed: judge the output, "an answer a tool or agent writes about a page" |
| 1 | fresh-eyes | RISK: curl gets an empty shell on a page built by JavaScript | fixed: "or a browser for a page built by JavaScript" |
| 1 | fresh-eyes | NIT: `-sL` hides errors | fixed: `-sSL` |
| 1 | fresh-eyes | NIT: the markup-stripping step should show | first refuted, wrongly; fixed in round 2 |
| 2 | Codex | BUG: the refutation missed that a READ may give a URL, not a command | fixed: "gives any step that strips its markup as a command too" |
| 3 | Codex | none | — |

Evidence sent each round: a curl capture of https://claude.com/docs/plugins/pre-submission-checklist
(200, 231,202 bytes, 2026-11-18T15:20Z) with its strip script, the round 1 finding from the paper
session, and the web-fetch agent's description. Not tested: other hosts' fetch tools, and the
browser example.

Cost: Codex 31,108 + 33,755 + 25,268 tokens; fresh-eyes 90,351; 180,482 in all.
