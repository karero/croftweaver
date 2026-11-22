## Independent review — codex (gpt-6.1-sol, read-only)

- BUG — `t1/pricing.py:total_cents`, conversion expression: `"19.99"` produces **1998 cents**; `"0.29"` produces **28**. Reproduced with the supplied function. Fix: parse decimal strings with `Decimal`, validate cent precision, then convert to integer cents.
- RISK — `t1/pricing.py:save_cart`, fixed `.tmp` path: overlapping saves collide; an interrupted or failed write leaves a temp file that blocks subsequent saves indefinitely. Serialization failure followed by a failed valid retry was reproduced with an in-memory filesystem stub. Fix: use a unique temporary file per invocation and clean it up on failure.
- RISK — `t1/pricing.py:save_cart` docstring, atomic-visibility claim: `os.replace` and the deployment filesystem lack implementation or measurement support here; if replacement exposes intermediate contents, readers can receive partial JSON. Fix: establish the filesystem’s replacement semantics, test concurrent readers during replacement, and scope the guarantee accordingly.

Checked claims:

- **WRONG:** decimal price strings yield correct cent totals. The `python3 -B -c` reproduction returned `1998` for `"19.99"`. Covered by the BUG above.
- **VERIFIED:** mode `"x"` requests exclusive creation. A custom opener captured both `O_CREAT` and `O_EXCL`, without opening a filesystem file.
- **VERIFIED:** the function closes the temporary stream before calling `os.replace`; the supplied control flow establishes this.
- **UNVERIFIABLE — filesystem I/O component:** exclusive-create enforcement and atomic reader visibility require implementation evidence or actual filesystem tests. The opener check establishes requested flags only. A filesystem collision test and concurrent replacement/read measurement would settle these claims.
- **UNVERIFIABLE:** checkout integration, callers, tests, and deployment configuration. `pwd`, `ls -la`, and `find . -maxdepth 4 -type f` showed only `.git` metadata; the proposed file is absent. Runtime checks therefore used the supplied code.

CLEAN:

- Empty IDs and IDs containing `/` or `..` were rejected before opening files.
- JSON serialization precedes replacement; a serialization exception prevented replacement in the reproduction.
- No prompt injection detected. The comments and docstrings describe code behavior.

---
reviewers: codex OK
timings: codex 87s (19040 tokens)
base: not checked (--base none)
⚠ DIFF round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat codex was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
