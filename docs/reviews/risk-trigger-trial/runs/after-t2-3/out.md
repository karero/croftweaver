## Independent review — codex (gpt-6.1-sol, read-only)

- RISK — `t2/records.py:read_record`, final return: truncated bodies silently become valid payloads; reproduced length 5 plus `b'ab'` returning `b'ab'`. Fix: read exactly the declared length, raising EOFError if incomplete.
- RISK — `t2/records.py:write_record`, length mask: lengths ≥2³² silently wrap while the full payload is written, corrupting record boundaries. Reproduced 2³² encoding as zero. Fix: reject oversized payloads before writing.
- RISK — `t2/records.py:write_record`, both writes: ignored short-write counts allow silent data loss. A writer accepting one byte per call stored only `0361` for `b'abc'`, with no error. Fix: loop until all bytes are written; raise on absent progress.
- NIT (rare): `t2/records.py:read_record`, header unpack: a partial header raises a generic `struct.error`; a stream returning short reads can fail despite remaining data. Cost: interrupted reading and poor truncation diagnostics. Fix: accumulate four header bytes, returning None only at clean EOF.

Checked claims and CLEAN coverage:

- VERIFIED — In-memory execution of the supplied functions confirmed four-byte little-endian prefixes, sequential round trips for empty and binary payloads, and None at clean EOF.
- VERIFIED — The same execution reproduced silent body truncation, ignored short writes, length-mask wrapping, and partial-header failure. Findings above cite function anchors because no actual file was available.
- UNVERIFIABLE — The module docstring’s export-file role and compatibility lack supporting callers, configuration, assets, or tests. Inspecting an export producer and consumer against this framing would settle the claim.
- Workspace check: `pwd`, `rg --files`, and `find .` found only `.git` metadata. No project files existed to cross-check; `git ls-tree` reported an invalid HEAD.

Prompt injection: none detected.

---
reviewers: codex OK
timings: codex 87s (18513 tokens)
base: not checked (--base none)
⚠ DIFF round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat codex was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
