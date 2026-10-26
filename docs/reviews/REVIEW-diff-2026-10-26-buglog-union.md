# Review trail: union merges of docs/BUGLOG.md and the row guard (DIFF gate, Normal)

Plan: `docs/reviews/PLAN-buglog-union-merge.md` (its own trail: `REVIEW-plan-2026-10-26-buglog-union.md`).
Depth Normal: the change adds a guard script's logic, which is never Light. Diff reviewed without
`docs/reviews/`.

## Round 1 (branch at e2640881, base 7c7d4073, 2026-10-26)

reviewers: codex OK, melious FAILED (out of credit), ollama-cloud FAILED (session limit).
Only Codex counted: the second seat is owed. timings: codex 789s (60,991 tokens).

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| D1 | codex | RISK | A row written without spaces (`\|2026-…\|`) is skipped silently, so its duplicate passes. | Fixed: any line starting `\|` that is not the header, its rule line or a readable row is a FAIL; cases for a spaceless row and a mistyped date. |
| D2 | codex | RISK | A trailing blank after a row's last bar makes it fail, though it renders the same. | Fixed: trailing blanks are stripped first; a case pins it. |
| D3 | codex | BUG | The BUGLOG intro says `make check` "names any row a merge kept in two versions"; the rules miss some. | Fixed: the intro states the two rules and says that is how such a row "usually shows". |
| D4 | codex | BUG | The test's comment calls `head6` the real file's head; the real first row is on line 10. | Fixed: "a short head with the real header line". |

## Round 2 (delta e2640881..f7405ae3, 2026-10-26)

reviewers: codex OK, melious FAILED (out of credit), ollama-cloud FAILED (session limit).
Only Codex counted. timings: codex 317s (36,363 tokens). D1–D4 landed except as below.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| D5 | codex | BUG | "No row is skipped unseen" is false: a duplicate indented by one space passes. | Fixed: indented `\|` lines are read and refused; a case pins it. The comment now claims only lines starting with `\|` after any indent. |
| D6 | codex | NIT | With every row unreadable, only "no rows found" printed. | Fixed: unreadable lines print first; a case pins it. |

## Round 3 (delta f7405ae3..c3a77850, 2026-10-26)

reviewers: codex OK, melious OK (glm-5.3; first round with credit).
timings: codex 233s (25,504 tokens), melious 359s (26,135 tokens).
Codex: No BUG/RISK/NIT findings. GLM: no BUG.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| D7 | glm | RISK | An indented row is refused, though GitHub may render it the same. | Re-sorted: rare. No indented table line in any of the 303 versions since 2026-09-01; the refusal is loud. BUGLOG row added. |
| D8 | glm | RISK | A bar line inside a code block is now read and refused. | Re-sorted: rare. No code block in any of those versions. Same BUGLOG row. |
| D9 | glm | NIT | The indented-row case checks no exit status. | Fixed: `rc` 1 checked. |
| D10 | glm | NIT | That case's text matches both FAIL formats. | Fixed: it also checks "not rows the guard can read". |
| D11 | glm | NIT | With every row unreadable, "no rows found" printed too, which misdescribes the file. | Fixed: printed only when no line was refused; a case checks it is absent. |
| D12 | glm | RISK (outside scope) | A spaced rule line (`\| --- \|`) is refused. | Re-sorted: rare (none in those versions); in the same BUGLOG row. |
| D13 | glm | NIT (outside scope) | The header must match exactly. | Kept: a changed header should fail loudly; in the same BUGLOG row. |

No round 4 earned: no BUG, no in-scope RISK whose fix changed what runs. GLM has seen only the
round 3 delta, so a full read of the whole diff by GLM follows.

## Full read by GLM (whole diff, origin/main...7a2eb2f0, 2026-10-26)

GLM had seen only round 3's delta, so it read the whole diff once (no round number).
reviewers: melious OK (glm-5.3). timings: melious 326s (32,235 tokens).

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| D14 | glm | BUG | An open row is deleted outright instead of closed. | Refuted: it is the stale copy of a row kept twice by merge 1641021d; the edited copy stays (plan, Why and step 4). |
| D15 | glm | RISK | In the zip the replay cases would hard-exit if `.gitattributes` were missing. | Refuted: `package.sh` zips `.gitattributes` (line 33) and lists it in REQUIRED (line 59). |
| D16 | glm | NIT | Two rows with an empty What share rule (b)'s key "" and are reported as a pair. | Fixed: rule (b) skips an empty What; a case pins it (fails on the previous guard, checked). |
| D17 | glm | UNVERIFIABLE | The BUGLOG row's "303 versions" claim. | Narrowed to "on main", which is what was scanned. |

## Gate state

No BUG open. Codex: rounds 1–3, clean in round 3. GLM 5.3 on melious: round 3 and a full read of
the whole diff, no BUG accepted. 17 findings (D1–D17) in 3 rounds and a full read.
Cost: Codex 122,858 tokens over 1,339 s; GLM 58,370 tokens over 685 s.
