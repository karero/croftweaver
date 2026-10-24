# SEO findings — <site> (<date>)

<!-- The diagnosis document. Every claim carries its data source (GSC export,
     serp_check.py snapshot). Distinguish GSC-confirmed (real impressions) from
     SERP-confirmed-only (we rank, nobody searches it yet). -->

## Headline
One paragraph: what the data says is broken, and the one-line strategy.

## The data
- Period, property, totals (clicks / impressions / avg position).
- Brand vs non-brand split — the mis-filing tell is brand-only demand.

## Queries — brand vs non-brand
| Query | Clicks | Impr | Pos | Brand? | Note |
|---|---|---|---|---|---|

## SERP competition (per candidate phrase)
For each phrase tested with the trap-test (market/lang explicit, snapshot saved):
- **Phrase** — verdict **✅ wedge / 🟠 crowded / 🚫 trap** — what the top-10
  *intent* actually is; who owns it; where (if anywhere) we appear.

## Keyword-fit research
Tested candidates across ≥2 rounds — replacements are often traps themselves.
Record rejected candidates WITH the reason (what Google returns instead), so
nobody re-proposes them later.

## One-line strategy
The wedge + the lanes, in one sentence each. Target-vs-copy caveats.

## Tracking
Where the predictions live (SEO-CHANGELOG.md), when grading runs, and by what
mechanism (scheduled task / CI cron / calendar).
