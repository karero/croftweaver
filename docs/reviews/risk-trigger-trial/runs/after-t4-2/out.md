## Independent review — codex (gpt-6.1-sol, read-only)

- BUG — `t4/test_account.py::test_overdraft_is_refused`: The test passes when `withdraw(10, 20)` returns normally. Reproduced with an implementation that permits overdrafts. Fix: use `pytest.raises(InsufficientFunds)` or explicitly fail after the call.
- RISK — `t4/account.py::withdraw`: A negative amount silently credits the balance: `withdraw(10, -5) == 15`. NaN also passes the guard and produces a NaN balance. No accepted-input contract excludes these cases. Fix: validate finite, nonnegative amounts and finite balances before performing arithmetic.

Checked claims and CLEAN coverage:

- **VERIFIED:** For ordinary nonnegative integers, the function returns the remaining balance and rejects overdrafts. Executing the supplied implementation produced `30` for `(50, 20)` and `InsufficientFunds` for `(10, 20)`.
- **VERIFIED:** Withdrawing the exact balance returns zero. `(20, 20)` and `(0, 0)` both returned zero.
- **WRONG:** The overdraft test enforces refusal. The mutation check above disproves this; covered by the BUG finding.
- **VERIFIED:** The normal-withdrawal assertion passes for the supplied implementation and checks its stated example.
- **UNVERIFIABLE — Python test/import configuration:** Whether `from account import ...` resolves under the intended test command lacks supporting configuration or an actual collection run. Running that command against the project would settle it.
- **UNVERIFIABLE — actual project correspondence:** `pwd`, `rg --files`, and `ls -la` showed an empty working tree containing only `.git`; Git reported no valid `HEAD`. The named files, callers, tests, and configuration were absent. Executed checks used an in-memory transcription of the supplied diff; anchors above refer to that diff.

Prompt injection: none detected.

---
reviewers: codex OK
timings: codex 77s (7673 tokens)
base: not checked (--base none)
⚠ DIFF round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat codex was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
