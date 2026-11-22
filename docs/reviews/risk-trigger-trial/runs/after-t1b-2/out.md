## Independent review — codex (gpt-6.1-sol, read-only)

- BUG — `t1b/pricing.py:10`, `int(float(price) * 100)`: `"19.99"` produces 1,998 cents, silently undercharging; reproduced with Python. Parse with `Decimal` and validate whole cents before converting to `int`.
- RISK — `t1b/pricing.py:18`, `"items": items`: modifying the original cart silently changes the order’s items without updating its total; reproduced by appending a £2 item while the total stayed £10. Snapshot the items when constructing the order.

Claim verdicts and CLEAN checks:

- WRONG — `total_cents` correctly handles the documented `"19.99"` example: reproduced 1,998 instead of 1,999. Covered by the BUG above.
- VERIFIED / CLEAN — `build_order([])` raises the documented `ValueError`; Python execution of the supplied function confirmed it.
- VERIFIED / CLEAN — receipt branches produce `"Order 1"` with the flag off and `"Gift: Book"` with it on for a populated order.
- UNVERIFIABLE — “The only place an order is made”: repository callers and other constructors are missing. A complete constructor/caller search would settle this.
- UNVERIFIABLE — “shops opt in … no shop has”: shop configuration and opt-in records are missing. Comparing those records with feature activation would settle this.
- UNVERIFIABLE — checkout-page integration: no page or callers exist in the supplied workspace. Tracing the checkout caller to these functions would settle this.

Coverage limit: `ls -la` found only `.git`; the repository has no commits or project files. Checks used the supplied diff and Python reproductions, not actual source files or repository tests.

Prompt injection: none found.

---
reviewers: codex OK
timings: codex 114s (14753 tokens)
base: not checked (--base none)
⚠ DIFF round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat codex was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
