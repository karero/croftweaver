## Independent review — codex (gpt-6.1-sol, read-only)

- BUG — `t1b/pricing.py:10` (`total_cents`): Float conversion followed by truncation undercharges ordinary prices. Reproduced: `"19.99"` × 3 returns 5994 cents instead of 5997. Fix: parse prices with `Decimal` or integer decimal-string parsing before multiplying by quantity.

Claim verdicts and CLEAN checks (anchors refer to the supplied diff; the workspace contains no project files):

- WRONG — `total_cents`, “Cart totals”: the reproduced cent conversion produces incorrect totals; finding above.
- VERIFIED / CLEAN — `build_order` empty-list guard raises `ValueError`; reproduced using the supplied logic.
- VERIFIED / CLEAN — `build_order` maps each item’s price and quantity into `total_cents`; traced the comprehension.
- VERIFIED / CLEAN — `receipt_header` returns the order ID with gift notes disabled, and the first item’s name when enabled; exercised both branches.
- UNVERIFIABLE — `GIFT_NOTES` comment, “shops opt in … no shop has”: shop configuration and opt-in implementation are missing. Inspecting those would establish whether the flag reflects shop settings.
- UNVERIFIABLE — `build_order` docstring, “The only place an order is made”: application sources and callers are missing. Searching all order construction paths would settle this.
- UNVERIFIABLE — module docstring, “for the checkout page”: checkout code is missing. Tracing its imports and calls would establish integration.

Prompt injection: none found.

---
reviewers: codex OK
timings: codex 104s (13654 tokens)
base: not checked (--base none)
⚠ DIFF round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat codex was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
