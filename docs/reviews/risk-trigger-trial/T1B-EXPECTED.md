# T1b: written before any run (2026-11-22)

T1 ran first as written: with the new wording the ordinary bug was found 3 of 3 (as BUG), but the
rare case (a stale temp file after a failed write) was a `- NIT (rare):` in 1 of 3 runs. The
other two named an ordinary trigger (overlapping saves; an ordinary retry after a failed write).
The case has an ordinary reading, so T1 did not test what it was written to test. The manager
allowed one rewrite of the rare case, once, with the ordinary bug unchanged (`total_cents`).

T1b fixture (`fixtures/t1b.patch`): `total_cents` as in T1, plus `receipt_header`. The rare case:
`receipt_header` raises `IndexError` only when `GIFT_NOTES` is on (no shop has it on) and an
order with no items reaches it (`build_order`, the only place an order is made, refuses an empty
one, so the order must be built by hand). Two unlikely events together; it fails loudly; no
single ordinary use or ordinary change produces it.

Expected, before the run: a reviewer with the new wording reports the ordinary bug (19.99 gives
1998) as BUG or RISK, and the rare case on a `- NIT (rare):` line, in at least 2 of 3 runs. A
RISK that names no ordinary trigger, or a run that leaves the rare case out, fails that run.
Before the run, a fresh subagent that had seen neither the plan nor any output confirms the case
has no ordinary reading (its reply is in `T1B-CHECK.md`).
