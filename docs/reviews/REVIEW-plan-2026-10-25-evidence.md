# Review trail: plan for `--evidence <file>` (PLAN gate, Normal)

Artifact: `docs/reviews/SKILL-PLAN-review-evidence.md`. Depth Normal: Codex (gpt-6.1-sol) + GLM
5.3 on melious, fresh-eyes (Sonnet) in round 1. No red team: the change touches no box, user
data, login, money, deletion or schema. Gate id 20261024T221701Z-6538.

## Round 1 (uncommitted draft, 2026-10-25)

reviewers: codex OK, melious FAILED ("HTTP 200: Insufficient balance for request. Required: 93,
Available: 0"), ollama-cloud FAILED (quota). Only Codex counted: the second seat is owed.
timings: codex 275s (110,055 tokens).

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F1 | codex | BUG | "the same diff with the evidence appended is refused, as today" is false: `diff_headers.pl` ignores text after the last hunk. | Confirmed by a probe (same `base:` line, exit 0, with and without a four-line appendix). Fixed: Why now says the case-study session used `--base none` because SKILL.md step 2 says so for a diff not made by `git diff`, and that the check would in fact have passed; the base-check test now gives the evidence a `diff --git` record the check refuses, so a leak would fail the run. The parser's leniency is a BUGLOG row (2026-10-25). |
| F2 | codex | RISK | The size test cannot protect the paste cut-off: Codex succeeds and the script exits before it. | Fixed: a second size run with every seat failing checks exit 4 and the "paste prompt is not printed" line. |
| F3 | codex | RISK | Order checks with wording and evidence together cover only codex and ollama; agy could put evidence before the wording paragraph and pass. | Fixed: the three plain-diff runs (default, agy, all failed) use `--evidence --wording-pass`, so every tier shows the wording paragraph before the evidence; Guards narrows the PLAN/VERIFY placement claim to codex and ollama. |

Fresh-eyes (Sonnet, on the plan with F1–F3 fixed): 248s, 192,223 tokens.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F4 | fresh-eyes | BUG | The size case cannot show "codex runs": the test's stub model `stub-codex` has no `seat_limits.txt` line, so codex keeps the 120,000 limit and FAILS. | Fixed: the case goes through case 38's `limitcase` with a `codex stub-codex takes:1040000` line; its all-failed half needs no stub failure, since seats with no line fail on size. |
| F5 | fresh-eyes | RISK | Order checks look at the lead's first line only, so its data sentences could be cut and every check pass. | Fixed: the lead's six lines are written out in the test and checked as one block, as in 25c. |
| F6 | fresh-eyes | RISK | Evidence lines are unprefixed, so the quota classifier can read an evidence log line as a quota error of a seat that failed for another reason. | Re-sorted: today's behaviour for every plan, and the FAILED section already says to treat a line from the reviewed material as a setup failure. Stated under Guards; not changed. |
| F7 | fresh-eyes | NIT | The END-marker refusal misses a trailing CR or blanks, and the plan overstates what it stops. | Fixed: matched after removing trailing spaces, tabs and CR; plan says it catches accidents, not attackers; a CR case added. |
| F8 | fresh-eyes | NIT | How 3's order sentence put the evidence lead among "scope paragraphs". | Fixed: wording. |
| F9 | fresh-eyes | NIT | Size messages are grepped by T11 and T13; plan did not say they stay unchanged without evidence, nor list every "artifact plus prior findings" comment. | Fixed: How 5 and Docs. |
| F10 | fresh-eyes | NIT | `evidence:` byte count ambiguous (file bytes or as read). | Fixed: counted as read, like CONTENT_BYTES; test uses a file ending in a newline. |
| F11 | fresh-eyes | NIT | SKILL.md's Output sentence and step 8 list the closing lines. | Fixed: Docs adds `evidence:` to both. |
| F12 | fresh-eyes | NIT | No plan + `--evidence` run, so placement against the guards paragraph is unchecked. | Fixed: Tests add it. |

Round 2 is earned by F1 and F4 (substantive BUGs).
