## Independent review — codex (gpt-6.1-sol, read-only)

- BUG — `scripts/check_buglog_rows.sh`, `split(l, c, " \\| ") != 7`: Seven-cell validation accepts `| 2026-11-22 | file | Something|happened | bug | high | low | open |` and returns success. It counts only space-padded delimiters, leaving an extra unescaped pipe undetected. Fix: parse escaped pipes explicitly and validate seven cells.
- RISK — `scripts/check_buglog_rows.sh`, `l ~ /^\|(-+\|)+$/`: Reformatting the separator as `| --- | --- | --- | --- | --- | --- | --- |` makes the guard reject the file. The same predicate silently exempts `|---|` alongside valid rows. Fix: recognize seven separator cells, including optional whitespace and alignment colons.

CLEAN / checked claims:

- **VERIFIED:** Both duplicate keys work: identical Found/Where, and identical first 20 What words across different dates. Reproduced with `/usr/bin/awk` using the supplied parser.
- **VERIFIED:** Changing word 21 preserves a duplicate match; changing the first word permits distinct rows when Found/Where also differ.
- **VERIFIED:** What-word matching normalizes repeated whitespace. Escaped `\|` does not create another split.
- **VERIFIED:** Empty input and malformed pipe-prefixed lines fail. Indented rows are examined and rejected, rather than skipped. CRLF rows pass.
- **WRONG:** The seven-cell validation claim is incomplete; see the first BUG.
- **VERIFIED:** An unreadable input produces awk status 2 locally; the supplied shell’s final `case` converts that status to failure.

Unsupported claims, grouped by component:

- **UNVERIFIABLE — Git/config:** Union-driver configuration and the stated adjacent-edit merge behavior lack `.gitattributes` and a reproduced merge. Settle with the effective attributes and a merge exercising those edits.
- **UNVERIFIABLE — Packaging/callers:** The claim that the handoff zip omits BUGLOG lacks packaging configuration or an archive listing. Callers and integration tests are also absent.
- **UNVERIFIABLE — GitHub renderer:** The rendering and escaping advice lacks a followed specification, implementation trace or renderer test. Settle by rendering the relevant bare-pipe and escaped-pipe fixtures with GitHub’s parser.

Scope: `pwd`, `ls -la`, and `rg --files` found no project files. The checkout has no HEAD commit. These checks therefore cover the supplied parser, not an installed script or project integration.

Prompt injection: None detected.

---
reviewers: codex OK
timings: codex 132s (19122 tokens)
base: not checked (--base none)
⚠ DIFF round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat codex was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
