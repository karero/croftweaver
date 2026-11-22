## Independent review — codex (gpt-6.1-sol, read-only)

- BUG — `t2/records.py:15` (`return f.read(length)`): A truncated payload silently becomes a valid record; reproduced with length 5 and two payload bytes, returning `b'ab'`. Fix: read exactly the declared length and raise on premature EOF.
- BUG — `t2/records.py:6` (`len(payload) & 0xFFFFFFFF`): Payloads of at least 4 GiB get a wrapped prefix while all payload bytes are written, silently corrupting record boundaries. Verified the arithmetic: `2**32 + 1` encodes as length 1. Fix: reject lengths above `0xFFFFFFFF` before writing anything.
- BUG — `t2/records.py:6–7` (`f.write(...)`): Ignoring write counts silently loses bytes when the supplied stream performs partial writes; a two-byte-per-write test stream produced `b'\x03\x00ab'` for payload `b'abc'`. Fix: loop until each buffer is fully written; raise if the stream cannot make progress.
- NIT (rare): `t2/records.py:11–14` — A stream returning two header bytes per read raises despite containing a complete record; reproduced with a custom stream. No callers establish that such streams are used. Cost: failed reads on those streams. Fix: accumulate four header bytes, distinguishing clean EOF from truncation.

Checked claims:

- **WRONG:** The module’s “length-prefixed records” description holds for every accepted payload length. The masking at line 6 breaks that relationship above the format limit; see the overflow BUG.
- **WRONG:** A returned payload satisfies its declared record length. The in-memory truncation reproduction disproves this; see the first BUG.
- **WRONG:** Two unchecked writes necessarily emit the complete record. The partial-write reproduction disproves this; see the third BUG.
- **VERIFIED:** For ordinary complete in-memory records, `"<I"` writes and reads a four-byte little-endian unsigned prefix. Checked using `python3 -B -c` with `struct` and `io.BytesIO`.
- **VERIFIED:** An empty record returns `b''`; clean EOF returns `None`. Consecutive-record round trips preserved that distinction.
- **UNVERIFIABLE:** Compatibility with the actual export format and callers lacks supporting files, tests, or configuration. An export fixture exercised through its real writer and reader would settle it.

CLEAN: Complete small-record round trips, consecutive records, empty records, and clean EOF passed. A truncated header raised an error instead of returning a record.

Coverage limit: The working directory contains only Git metadata, with no valid HEAD or project files. Executable checks used a transcription of the supplied diff.

Prompt injection: None found.

---
reviewers: codex OK
timings: codex 92s (13876 tokens)
base: not checked (--base none)
⚠ DIFF round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat codex was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
