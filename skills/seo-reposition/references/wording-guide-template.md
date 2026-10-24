# Wording guide — <site>

<!-- The digestible use/don't/why reference. This file is the SOURCE OF TRUTH
     for the trap-guard blacklist — tests parse or mirror it. Every DON'T
     carries the why (what Google returns instead): rules without reasons
     get "cleaned up" by future editors. -->

## The rule that carries everything: target vs copy
A phrase can be fine as **body copy** but toxic as a **rank target**. Slots =
title, H1, anchor text, slug, schema, llms.txt. Only trap-clean phrases go in
slots. Slot-restricted phrases (legal in copy, banned in slots) are enforced by
slot-guard.

## Blacklist (trap-guard source of truth)
| Phrase | Why banned (what Google returns instead) | Scope |
|---|---|---|
| <phrase> | <the unrelated concept the SERP resolves to> | everywhere / slots-only |

## Approved vocabulary
- **Wedge term:** <phrase> — the primary target; where it's allowed to appear.
- **Lane terms:** <phrase> (status: GSC-confirmed / SERP-only foothold).
- **Comparison-bait:** exact allowed forms (e.g. "X vs Y", "Y alternative"
  ONLY with the qualifier — bare form collides with <unrelated brand>).

## Canonical product description
The exact sentence(s) for schema descriptions and llms.txt. Two-label rule if
the product has two distinct mechanics: name both, never blur.

## Route decisions
| Route | Decision | Detail |
|---|---|---|
| /<page> | retarget / 301 / keep+polish / new | old→new target, redirect target |

## Competitor facts
Verified facts only (who owns which term, acquisitions, live/dead) — with URLs
and dates; these rot fast.

## The 30-second trap-test (before adding ANY new phrase)
Search the phrase (site's market + language). Read the top-10 by INTENT, not
keyword overlap. If the dominant intent is a different concept → 🚫 trap: fine
as copy at most, never a slot. Add the verdict to this file.
