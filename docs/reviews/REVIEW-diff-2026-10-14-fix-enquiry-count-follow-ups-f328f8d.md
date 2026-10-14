# Review trail: enquiry-count follow-ups (W2, H4), branch fix/enquiry-count-follow-ups

DIFF gate. **Depth: Normal**: the starter's test is copied into owners' sites, and `new-website/SKILL.md` is an instruction file, so Light does not apply. Round 1: Codex, GLM 5.3 on melious, fresh-eyes (sonnet).

## Rounds

| Round | Head | Reviewers | BUG / RISK / NIT | Outcome |
|---|---|---|---|---|
| 1 | f328f8d | codex 302 s 90k tok; melious glm-5.3 291 s 17k tok; fresh-eyes (sonnet) 103 s 112k tok | 0 / 2 / 5 | fixes change test logic; round 2 owed |

## Findings

| Id | Sev | Source | Round | Location | Finding | Status | Evidence |
|---|---|---|---|---|---|---|---|
| A1 | RISK | codex | 1 | `email.spec.ts` `pagesWithEmail` | `/\sdata-email="/` needs a double quote: other quoting would make the `%` test skip in silence. | fixed, locally_verified | now `/\sdata-email=/`; node: true for double, single and no quotes, false for `data-other-data-email=` and the script's `[data-email]` |
| A2 | RISK | codex, melious | 1 | Q5, README, BUGLOG row, plan | "a self-hosted instance would show earlier taps" rests on one function, not the traced query path, and conflicts with the docs while the cloud runs the same code. | fixed, locally_verified | owner docs repeat only Plausible's documentation; the plan keeps the source reading, marked as one function read and the rest left open |
| A3 | NIT | fresh-eyes | 1 | README | self-hosted claim without a version | fixed | the claim is gone (A2) |
| A4 | NIT | fresh-eyes, melious | 1 | plan | "as Safari does" unsupported | fixed | "whether Safari does the same was not checked" |
| A5 | NIT | fresh-eyes, melious | 1 | `new-website/SKILL.md` Q5 | over-long line | fixed | rewrapped |
| A6 | NIT | fresh-eyes | 1 | plan | "Delivery" overstates: requests were answered locally | fixed | "Request sent"; says no Plausible server received them and no content blocker was in the way |
| A7 | NIT | melious | 1 | BUGLOG row | parenthetical drops the hedge | fixed | removed (A2) |
