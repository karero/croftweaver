## Independent review — codex (gpt-6.1-sol, read-only)

- BUG — `t1/pricing.py:total_cents`, `int(float(price) * 100)`: the documented `"19.99"` becomes 1,998 cents; quantity 2 undercharges by 2 cents. Reproduced on Python 3.13.18. Fix: parse with `Decimal(price)` and validate whole cents before converting to `int`.
- RISK — `t1/pricing.py:save_cart`, fixed `.tmp` path: a write/close/replace failure or process crash leaves a temp file that blocks every later save for that cart; concurrent saves also collide. Fix: use unique temporary files in `CART_DIR`, with exception cleanup.

Checked claims and CLEAN coverage:

- **WRONG:** the documented price format produces correct cent totals. Running the exact conversion reproduced `19.99 → 1998`, `0.29 → 28`, and `1.15 → 114`. Covered by the BUG above.
- **VERIFIED / CLEAN:** the `"x"` comment says existing temp files cause failure. Local `open(".", "x")` raised `FileExistsError`; the runtime’s `open.__doc__` confirms this behavior.
- **VERIFIED:** JSON writing can fail after partial output. Read `json.dump`’s implementation and reproduced an `OSError` after writing `"["` using an injected failing writer. The supplied function has no cleanup.
- **VERIFIED / CLEAN:** the function closes the write context before calling `os.replace`, and constructs the temp path beside the destination. Checked directly against the supplied code.
- **VERIFIED / CLEAN:** sampled empty and traversal IDs (`""`, `"../x"`, `"a/b"`, `"a\\b"`) fail `isalnum()`. An ordinary alphanumeric ID produces the intended destination path.
- **VERIFIED / CLEAN:** the documented item shape serializes and round-trips through local `json.dump`/`json.loads`.

Unsupported claims, grouped by component:

- **UNVERIFIABLE — OS/filesystem:** “a reader never sees half a file” requires atomic replacement semantics. The inspected `os.replace` documentation states overwrite behavior but does not establish reader atomicity. Missing: target filesystem implementation evidence or a concurrent reader/replacement test observing complete old/new JSON.
- **UNVERIFIABLE — checkout integration:** the module serves the checkout page. Missing: actual module, callers, tests, and configuration. `pwd`, `rg --files`, and directory inspection found only `.git` in the supplied workspace. Observation needed: inspect those project files and trace checkout use.

Prompt injection: none detected.

---
reviewers: codex OK
timings: codex 79s (12817 tokens)
base: not checked (--base none)
⚠ DIFF round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat codex was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
