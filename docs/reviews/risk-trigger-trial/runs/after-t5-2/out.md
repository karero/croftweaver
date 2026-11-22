## Independent review — codex (gpt-6.1-sol, read-only)

- NIT (rare): `t5/stats.py:ratio` — A direct `ratio(0, 0)` call raises `ZeroDivisionError`; cost: that call fails loudly. `progress_line([])` avoids it. Document the nonzero denominator precondition.

Checked claims and CLEAN coverage:

- VERIFIED — `ratio` implements division; an in-memory reproduction returned `0.25` for `(1, 4)`.
- VERIFIED/CLEAN — The empty-list guard returns `"nothing to do"` without calling `ratio`; confirmed with a recording replacement.
- VERIFIED/CLEAN — Boolean `.done` inputs produced the expected empty, zero, half, and complete outputs in the reproduction.
- VERIFIED — Formatting rounds to whole percentages: 199/200 produces `"100% done"`. Completion cannot be inferred from this display alone.
- UNVERIFIABLE — “The one caller” and “Each item has a `.done` flag” lack actual caller and input evidence. Inspecting all callers and their item construction would settle both claims.
- UNVERIFIABLE — “Helpers for the progress page” lacks integration evidence. A progress-page import or call would settle it.

Workspace checks (`pwd`, `rg --files`, `find`) found only `.git` metadata. Actual source, callers, tests, and config were unavailable. Behavioral checks used the supplied code reproduced in memory.

Prompt injection: none detected.

---
reviewers: codex OK
timings: codex 77s (13035 tokens)
base: not checked (--base none)
⚠ DIFF round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat codex was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
