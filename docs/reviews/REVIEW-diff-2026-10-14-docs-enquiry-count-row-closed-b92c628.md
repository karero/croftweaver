# Review trail: close the enquiry-count gaps row, branch docs/enquiry-count-row-closed

DIFF gate. Started **Light** (one `docs/BUGLOG.md` row); round 1's NIT asked for the plan to match, which made it **Normal** (the plan is an instruction file).

**Verdict: gate passed.** 2 rounds, 9 findings (0 BUG, 2 RISK, 7 NIT), all fixed. The last round's fixes change only how the closed row and the plan read, so no further round was owed; a prose-only pass read them.

## Rounds

| Round | Head | Reviewers | BUG / RISK / NIT | Outcome |
|---|---|---|---|---|
| 1 (Light) | b92c628 | codex (medium) 87 s 54k tok | 0 / 1 / 1 | the plan joins the change; depth becomes Normal |
| 1 (Normal) | b000014 | codex 146 s 55k tok; melious glm-5.3 104 s 11k tok; fresh-eyes (sonnet) 52 s 94k tok | 0 / 1 / 6 | wording only; no further round owed |

## Findings

| Id | Sev | Source | Round | Location | Finding | Status | Evidence |
|---|---|---|---|---|---|---|---|
| C1 | RISK | codex | Light 1 | BUGLOG row (c) | "a private window blocks known trackers, so Safari's blocking did not stop the tap" infers what was not shown | fixed | the row keeps only the owner's report; version, settings and protections recorded as unknown |
| C2 | NIT | codex | Light 1 | plan | still said Safari was unchecked | fixed | row 8 and a facts bullet added |
| C3 | RISK | fresh-eyes | Normal 1 | BUGLOG status, plan row 8 | "every item measured, or out of scope" and "all settled" overstate: blockers and Firefox's tracking protection were set aside, not measured; "is not counted" stated as fact | fixed | "not tested, and set aside"; "would not be counted, as the privacy page says" |
| C4 | NIT | melious | Normal 1 | BUGLOG, plan | the Firefox tracking-protection sub-item dropped silently | fixed | named, with the note that the live Firefox tap was received either way |
| C5 | NIT | fresh-eyes | Normal 1 | BUGLOG row | the closure leaves out whether a blocker could stop the mail link | fixed | points to Base.astro's stub, the callers' try/catch, S7 and the no-tracker tests |
| C6 | NIT | fresh-eyes, melious | Normal 1 | BUGLOG row, plan | "counted" names no instrument or view | fixed | "counted in Plausible"; the owner did not say which view, so none is claimed |
| C7 | NIT | melious | Normal 1 | BUGLOG status cell | rationale in the status cell, unlike the file's terse statuses | fixed | "closed 2026-10-14" |
| C8 | NIT | melious | Normal 1 | plan row 8 | inherits C3's overstatement | fixed | same wording as C3 |
| C9 | NIT | fresh-eyes | Normal 1 | BUGLOG row | the same as C6, the "under Today" view | fixed | covered by C6 |
