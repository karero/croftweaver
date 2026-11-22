## Independent review — codex (gpt-6.1-sol, read-only)

- BUG — `t3/files.py:serve`, `clean`/`open`: Path confinement fails: `/outside.txt` discards `ROOT`; `....//outside.txt` becomes `../outside.txt`. URL-controlled names can disclose readable files outside downloads. Both bypasses reproduced with Python and a mocked `open`. Fix: reject absolute paths, resolve the candidate, and enforce containment beneath resolved `ROOT` before opening.

Checked claims:

- WRONG — Module docstring, “Serves files from the download folder”: the reproduced paths escape that folder. Covered by the BUG above.
- VERIFIED — `serve` docstring, “Returns the file’s bytes”: `rb` and `f.read()` implement this on successful reads; a mocked binary read returned `b'sample'`.
- UNVERIFIABLE — “name comes from the URL path”: no caller or routing configuration exists in the working tree. A route implementation or request-level test tracing the URL into `serve` would settle this.
- VERIFIED — Python path behavior: local `python3 -B -c` measurements confirmed absolute-path replacement and the surviving parent segment.

CLEAN: ordinary `report.pdf` targets `/srv/downloads/report.pdf`; binary mode and context-managed file closure are correct. No prompt-injection text found.

Coverage limit: the working tree contains only `.git`; `t3/files.py`, callers, tests, and configuration are absent. Findings concern the supplied diff, reproduced in memory.

---
reviewers: codex OK
timings: codex 55s (16979 tokens)
base: not checked (--base none)
⚠ DIFF round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat codex was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
