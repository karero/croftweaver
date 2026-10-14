# DIFF review — independent-review: a severity bar, cut instead of patch, cheaper rounds, the split, a cost notice
Base `e038603` · depth: Normal (the change is an instruction file agents load; it touches no script, prompt or test) · verdict: CLEAN — three rounds; round 3 had no BUG and no RISK, its three NITs fixed after it ("closing edits not externally re-verified"); about 37 findings across all seats before merging duplicates (9 labelled BUG, 13 RISK, 15 NIT), every one fixed in the text.

What it is: the lessons of the brand-kit gate (karero/croftweaver#283: nine rounds over about 31 hours, about 37 million tokens), written into the review skill as five rules the owner chose on 2026-10-14 from six offered: "Severity bar", "Cut, don't patch", "Cheaper rounds", "Split big changes", "Cost notice". The sixth, "Owner decides at round 5", was not chosen: the owner's decision stays past round 8. `references/rationale.md` gains the incident.

Data check: prose only, no key, token or password. Destinations: Codex and GLM 5.3 on melious, the repo's standing pair.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT (all seats) |
|---|---|---|---|---|---|
| 1 | `a7ba185` | full: `e038603...a7ba185` without `docs/reviews/` | codex-cli 0.162.1, config effort, read-only; melious glm-5.3 (text only); fresh-eyes: a sub-agent one size down, read-only | codex 311 s / 91,071; glm 290 s / 16,229; fresh-eyes 149 s / 123,057 | 7 / 11 / 8 |
| 2 | `4d4eb9f` | `a7ba185..4d4eb9f`, with round 1's record (`--verify`) | the pair, Codex at medium | codex 177 s / 63,475; glm 293 s / 26,718 | 2 / 2 / 3 |
| 3 | `06d3074` | `4d4eb9f..06d3074`, with round 2's record | the pair, Codex at medium | codex 67 s / 33,073; glm 90 s / 9,706 | 0 / 0 / 3 |

Total: about 363,000 tokens.

| Round | Finding — one line | Status |
|---|---|---|
| 1 | the seats were said to give the ORDINARY / MADE BY HAND mark, but no prompt asks and the tooled prompt makes every WRONG a BUG | fixed: the host sets the mark; prompts unchanged |
| 1 | a crash on hand-made input was both a BUG and a "safe stop" | fixed: a safe stop is defined; a crash, a hang or an uncaught error is never one |
| 1 | "part" undefined; fresh-eyes at High limited to "code" left prose fixes unread | fixed: the trail names parts before round 1 (a change without them is one part); fresh-eyes reads each part a fix changed, by step 6's test |
| 1 | "the final full read covers it" untrue at Normal; one PR does not by itself mean every part re-read | fixed: "at High"; the split's reason is a kind of defect found again per component |
| 1 | step 6's cut and step 7's stop had one trigger and two actions | fixed: step 7 stops when a kind that has had its cut comes back |
| 1 | a stated limit offered as the cut for any BUG | fixed: only where what is left falls under the bar's NIT |
| 1 | a BUG demoted by the bar needed no owner notice; the bar's scope | fixed: each demotion listed for the owner (steps 4 and 8); the bar applies to DIFF gates on code |
| 1 | net-negative lines as a hard rule; Codex at medium for High fixes unsupported; tests per round before "the next round" only; cost notice once; closeout and rationale sentences now false; smaller wording | fixed: the line count is reported, not required; config effort for a fix on anything High names; "the next round, the wording pass or closeout"; the notice repeats; both files in line |
| 2 | "High trigger" listed five of the row's categories; the rationale and closeout sentences; four wording points | fixed |
| 3 | three wording NITs | fixed after the round |

Refuted: none. Deferred: none. Waivers: none. Follow-ups: none.

Not done: the wording pass did not run as a separate pass; round 3, a full verification of round 2's text, was clean, and only three NIT-sized edits came after it.
