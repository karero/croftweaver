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
