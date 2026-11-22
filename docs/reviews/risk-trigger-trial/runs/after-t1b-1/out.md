## Independent review — codex (gpt-6.1-sol, read-only)

- BUG — `t1b/pricing.py:total_cents`, `int(float(price) * 100)`: **WRONG** cents conversion silently undercharges ordinary prices; Python reproduction gives `"19.99"` → 1998 and `"0.29"` → 28. Fix: parse decimal strings exactly with `Decimal`, validate whole cents, then multiply by quantity.
- RISK — `t1b/pricing.py:build_order`, returned `"items": items`: editing the original cart after creating an order silently changes its items while retaining its old total; reproduced 350 cents of items with total 250. Fix: snapshot the item tuples into an immutable sequence before computing and storing the total.

Checked claims and CLEAN behavior, using the supplied functions executed in memory with `python3 -B -c`:

- **VERIFIED / CLEAN:** `build_order` rejects an empty list with `ValueError`.
- **VERIFIED / CLEAN:** empty cart totals zero; `"2.50"` × 3 totals 750 cents.
- **VERIFIED / CLEAN:** the default receipt returns `Order A`; enabling `GIFT_NOTES` returns the first item’s name for a nonempty order.
- **VERIFIED / CLEAN:** `build_order` correctly extracts price and quantity from the documented triples.
- **UNVERIFIABLE — shop configuration:** “shops opt in … no shop has” lacks configuration or deployment evidence. Settle it by inspecting the active shops’ gift-note settings.
- **UNVERIFIABLE — construction and integration:** “The only place an order is made” and checkout-page integration lack callers, tests, and application files. Settle them by tracing order producers and checkout consumers in the actual project.

Scope: `pwd`, `ls -la`, and `rg --files` showed only `.git`, with no project files. Anchors above refer to the supplied diff; actual-file verification remains unavailable.

Prompt injection: none found.

---
reviewers: codex OK
timings: codex 104s (10903 tokens)
base: not checked (--base none)
⚠ DIFF round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat codex was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
