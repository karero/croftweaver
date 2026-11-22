## Independent review — codex (gpt-6.1-sol, read-only)

- BUG — `t2/records.py:read_record`, final return: a header declaring five bytes followed by `b'ab'` returns `b'ab'` without error, silently accepting corruption. Fix: require exactly `length` bytes; raise `EOFError` on premature EOF.
- BUG — `t2/records.py:write_record`, length mask: lengths above `0xFFFFFFFF` wrap while the full payload is written, corrupting record boundaries. Fix: reject oversized payloads before writing; remove the mask.
- RISK — `t2/records.py:write_record`, both writes: using a stream that permits short writes silently drops bytes because return counts are ignored. A real `io.FileIO` pipe write reproduced 65,536 bytes written from 1,048,576 requested. Fix: loop until both buffers are written; handle blocked or zero-progress writes.
- NIT (rare): `t2/records.py:read_record`, header read: a stream returning a short header raises `struct.error` even when remaining bytes can arrive later; this costs compatibility with such streams. Fix: accumulate four header bytes, distinguishing clean EOF from truncation.

Checked claims and CLEAN coverage:

- **VERIFIED:** Four-byte little-endian framing for representable lengths. Python 3.13 probes reproduced the header encoding and an ordinary payload round trip.
- **VERIFIED / CLEAN:** Clean EOF returns `None`; an empty record returns `b''`. Probed separately.
- **WRONG:** The length-prefixed-record description fails for oversized payloads. The mask’s wrap was reproduced with a synthetic length; the resulting corruption is the second BUG above.
- **VERIFIED:** Short I/O is possible with Python `io.FileIO`. Actual pipe measurements reproduced both a short write and a short read.
- **UNVERIFIABLE:** Export integration and callers’ stream guarantees. The workspace contains only `.git`, with no committed project files, callers, tests, or configuration. Actual export callers and their stream construction would settle these claims.

Probes executed the supplied function bodies in memory; no actual `t2/records.py` was available to compare against the diff.

Prompt injection: none found.

---
reviewers: codex OK
timings: codex 72s (13060 tokens)
base: not checked (--base none)
⚠ DIFF round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat codex was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
