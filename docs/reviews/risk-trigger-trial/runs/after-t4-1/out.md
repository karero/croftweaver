## Independent review — codex (gpt-6.1-sol, read-only)

- BUG — `t4/test_account.py:test_overdraft_is_refused`: The test passes when `withdraw` never raises. Replacing it with unchecked subtraction reproduced this. Use `with pytest.raises(InsufficientFunds): withdraw(10, 20)`.
- RISK — `t4/account.py:withdraw`: A negative amount silently credits the balance: `withdraw(50, -20)` returns `70`. Reject negative amounts and test that rejection.
- RISK — `t4/account.py:withdraw`: Nonfinite floats silently corrupt the returned balance: `withdraw(10, float("nan"))` returns `nan`; infinity minus infinity does too. Reject nonfinite inputs before comparison or subtraction.

Claim verdicts and CLEAN checks:

- VERIFIED — Normal withdrawal returns the expected balance: the supplied test body passed in an in-memory execution of the diff.
- VERIFIED — The implementation refuses the illustrated overdraft, `withdraw(10, 20)`, by raising `InsufficientFunds`.
- WRONG — The overdraft test enforces refusal. The unchecked-subtraction mutation passed that test. Covered by the BUG above.
- CLEAN — No prompt injection appears in the diff.

UNVERIFIABLE — Actual-file agreement, callers, input contracts, pytest discovery, and configuration. `pwd`, `ls -la`, and `rg --files --hidden` found only `.git`; `git ls-tree -r --name-only HEAD` reported no valid `HEAD`. These checks require the project files and test configuration. Execution above covered reconstructed diff code and test bodies, not repository tests.

---
reviewers: codex OK
timings: codex 76s (11084 tokens)
base: not checked (--base none)
⚠ DIFF round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat codex was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
