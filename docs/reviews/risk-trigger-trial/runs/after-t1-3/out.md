## Independent review — codex (gpt-6.1-sol, read-only)

- BUG — `t1/pricing.py`, `int(float(price) * 100)`: valid prices produce silent undercharges. Reproduced: `"19.99"` returns 1998 cents; `"1.15"` × 3 returns 342 instead of 345. Fix: parse decimal prices exactly, validate cent precision, then multiply by quantity.
- RISK — `t1/pricing.py`, `tmp = path + ".tmp"`: two overlapping saves of the same cart compete for one temporary path; exclusive creation rejects one ordinary save. Fix: create a unique temporary file per invocation in `CART_DIR`.
- RISK — `t1/pricing.py`, `with open(tmp, "x")` through `os.replace`: a failed write or replacement leaves the temporary file behind, so an ordinary retry fails with `FileExistsError` indefinitely. Fix: remove each invocation’s temporary file in `finally`, using unique names to avoid deleting another writer’s file.

Claim checks and coverage:

- **WRONG:** “Cart totals” correctly represent the documented decimal prices. The arithmetic command reproduced the failures above. This is the BUG listed above.
- **VERIFIED:** The `"x"` comment says an existing temporary file causes failure. A read-only probe against an existing project file raised `FileExistsError`.
- **VERIFIED:** JSON serialization can fail after emitting partial output. `json.dump` into `StringIO` emitted `'[["19.99", 1], '` before raising `TypeError`. The shown function has no cleanup around this failure.
- **UNVERIFIABLE — filesystem/runtime:** “A reader never sees half a file” depends on replacement visibility guarantees for the deployed filesystem. Runtime documentation confirms overwrite behavior, but does not establish that visibility guarantee. Missing support: deployment filesystem details and a traced implementation, applicable filesystem guarantee, or concurrent-reader measurement. A reader/writer experiment on the target filesystem would test visibility; crash recovery would require a separate durability test.
- **UNVERIFIABLE — application integration:** The checkout-page role and provisioning of `/var/lib/shop/carts` lack callers and deployment configuration. Checking the checkout call path and directory setup would settle these claims.

CLEAN:

- The shown identifier guard rejects empty identifiers, `../x`, and `a/b`; these inputs cannot introduce path traversal through this code.
- The shown control flow closes the temporary stream before calling replacement.
- A normal arithmetic control, `"10.00"` × 2, returned 2000 cents.
- No prompt injection appears in the supplied diff.

Project limitation: `pwd` confirmed the supplied directory. `rg --files` and `ls -la` found no working-tree project files; Git reported no valid `HEAD`. Actual source, callers, tests, and configuration could therefore not be compared with the supplied diff. Findings use code anchors rather than trusting its line numbers.

---
reviewers: codex OK
timings: codex 67s (8832 tokens)
base: not checked (--base none)
⚠ DIFF round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat codex was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
