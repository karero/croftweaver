# T1b: the fresh subagent's check, before any run (2026-11-22)

A fresh subagent saw only the fixture's code and the question "what conditions make `receipt_header`
raise, is each one produced by an ordinary use or one ordinary change, and does the exception need
two or more unlikely events together?" It had seen neither the plan, the wording nor any output.
Its conclusion, in its words: no single ordinary use or single ordinary change produces the
exception; flipping `GIFT_NOTES` is ordinary but harmless until an order that `build_order` would
never create reaches `receipt_header`, so it takes the flag plus a bypass, mutation or generator:
two things together, one of them unlikely. It fails loudly (IndexError, TypeError or KeyError).

Note for the reader: the subagent counts the flag flip as an ordinary change, not an unlikely
event. The case is therefore "one ordinary change plus one unlikely event", not "two unlikely
events"; the check it answers, "no ordinary reading", holds. The case was run as written, once.

## Correction after the Codex Light review of this record (2026-11-22)

The check was wrong. `build_order` stores the caller's `items` list as it is. A caller that
enables `GIFT_NOTES`, builds an order, then clears the cart list leaves `order["items"]` empty, and
`receipt_header` raises `IndexError` (Codex reproduced it). No bypass of `build_order` is needed.
Two of the three T1b runs raised the aliasing as a RISK. The fresh subagent read the code and did
not find this path, so "a fresh reader finds no ordinary reading" is not a test of one.
