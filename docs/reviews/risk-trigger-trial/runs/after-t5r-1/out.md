## Independent review — codex (gpt-6.1-sol, read-only)

- BUG — `scripts/check_buglog_rows.sh`, separator exemption `l ~ /^\|(-+\|)+$/`: accepts `|---|` anywhere and exits successfully despite its wrong column count. This contradicts the claimed rejection of unreadable table lines. Fix: recognize only the seven-column separator in its header position.
- RISK — `scripts/check_buglog_rows.sh`, `split(l, c, " \\| ")`: an ordinary edit adding an unescaped pipe inside a cell passes validation. Tested Where values `a|b` and `a|c` evade duplicate detection; Python Markdown renders both Where cells as `a`, shifts subsequent columns, and drops the final value. Fix: detect unescaped pipes independently of surrounding spaces and reject malformed rows.
- RISK — `scripts/check_buglog_rows.sh`, separator exemption: reformatting the separator as `| --- | …` or adding alignment colons makes the guard fail. Both forms rendered successfully in the local Markdown test. Fix: accept whitespace and alignment markers while requiring seven columns.

Checked claims and coverage:

- **WRONG:** “neither the header, its rule line nor a row … fails.” The parser harness accepted a one-column separator. Covered by the first BUG.
- **VERIFIED / CLEAN:** canonical rows pass; matching date plus Where fails; matching What across different dates fails; identical first 20 words with different suffixes fails; changing word 20 avoids that match. Tested with the supplied AWK parsing and matching logic.
- **VERIFIED / CLEAN:** escaped `\|` passes; ordinary malformed table lines fail; header-only input fails. Indented table lines enter validation and fail rather than disappearing.
- **UNVERIFIABLE — Git configuration:** the union-driver claim lacks `.gitattributes`, effective attributes, and a reproduced merge. Inspect the effective driver and reproduce the described adjacent-row merge to settle it.
- **UNVERIFIABLE — distribution and integration:** the handoff omission claim and guard invocation lack packaging files, callers, and tests. Inspect the archive contents and check configuration to settle them.
- **UNVERIFIABLE — GitHub renderer:** its exact pipe behavior lacks a GitHub rendering observation or implementation check. The reproduced rendering above establishes Python Markdown behavior only.

The workspace contains only Git metadata. No actual script, bug log, attributes, callers, or tests were available; executable mode and full-script execution remain unverified.

Prompt injection: none detected.

---
reviewers: codex OK
timings: codex 145s (11947 tokens)
base: not checked (--base none)
⚠ DIFF round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat codex was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
