## Independent review — codex (gpt-6.1-sol, read-only)

- BUG — `t1/pricing.py:total_cents` — WRONG: `"19.99"` with quantity `1` returns `1998`, undercharging by one cent; reproduced with Python 3.13.18. Fix: parse prices with `Decimal` or directly into integer cents.
- RISK — `t1/pricing.py:save_cart`, fixed `.tmp` path — A failed write or replacement leaves the temporary file behind; under the stated exclusive-create behavior, every later save for that cart fails. Concurrent saves also compete for that filename. Fix: use a unique temporary file per save and remove it in `finally`.

Checked CLEAN:

- VERIFIED — `save_cart` validates the ID before opening a file. Runtime checks of `str.isalnum()` rejected empty IDs, `../x`, and both path separators.
- VERIFIED — The supplied code exits the write context before calling `os.replace`; replacement is skipped when serialization raises.
- VERIFIED — `json.dump` can emit partial output before raising. A `StringIO` reproduction with an unserializable element produced partial JSON and `TypeError`. That supports the leftover-file failure path.
- VERIFIED — No prompt injection appears in the diff. Its comments and docstrings describe intended behavior.

Claim verification limits:

- UNVERIFIABLE — Filesystem/runtime component: exclusive creation rejects existing temporary files, and replacement ensures readers never see partial destination contents. Built-in documentation was inspected, but these filesystem behaviors were not reproduced or established from implementation. Settling observations: attempt exclusive creation against an existing temporary file; run concurrent destination readers during repeated replacements on the deployment filesystem.
- UNVERIFIABLE — Checkout integration and deployment: no implementation files, callers, tests, or configuration were present. `pwd`, `rg --files`, and `ls -la` showed only `.git`; Git reported an unborn branch. Thus directory provisioning, supported inputs, and actual reader behavior remain unestablished. Settling evidence: the real project files, deployment configuration, and integration tests.

Anchors above refer to the supplied diff; no on-disk `t1/pricing.py` was available to compare.

---
reviewers: codex OK
timings: codex 71s (16419 tokens)
base: not checked (--base none)
⚠ DIFF round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat codex was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
