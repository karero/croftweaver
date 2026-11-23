# DIFF review: write the brief before asking about a competing page (2026-11-23)

Base: `origin/main` at `501b26e6`. Depth: Normal (SKILL.md is never Light). Seat: Codex alone, with a
fresh-eyes pass (a Sonnet subagent that did not write the change) at round 1. The script's warning
that the standard pair was not met applies.

Why the change: in the behaviour tests of #646, one agent asked the owner before the draft as step 3
said, but wrote no brief at all. Step 3 now says the brief comes first.

| Round | Reviewer | BUG / RISK / NIT | What came back |
|---|---|---|---|
| 1 | Codex | 0 / 0 / 0 | clean |
| 1 | fresh-eyes | 0 / 2 / 2 | the brief could stay stale after the owner's answer; several competing pages left the number of decisions unclear; "Otherwise" read badly; *narrow* needs the page's new sentences |
| 2 | Codex | 0 / 1 / 0 | with one decision per page, two pages could both be extended |
| 3 | Codex | 0 / 0 / 0 | clean |

All four fresh-eyes findings and the round 2 RISK were fixed: each listed page gets its own decision,
at most one page is extended and the others are judged against it, the answer goes into the field
(for *narrow*, with the new sentences), and every brief field it changes is revised before the draft.

Tokens: Codex 35,876, 44,368 and 35,960; fresh-eyes 93,363.

Not tested: no test covers step 3 or the template field. Test 26 pins only the content-review prompt.
