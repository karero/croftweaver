# DIFF review — `website-new-page` mode for moving a page from an old site

Plan: `website-new-page/PLAN-migrated-pages.md` in the private hub (reviewed; the owner's go of
2026-11-09). Depth: Normal (skill text a builder follows, and runtime code in `gsc_query.py`; no box,
user data, login, money, deletion or schema). Seats: Codex gpt-6.1-sol; the second seat, GLM 5.3 on
melious, failed in round 1 with an empty balance, so by the owner's rule of 2026-10-27 the gate
stands on Codex alone (rounds 2 and 3 ran `--seat codex`). Round 1 also had a fresh-eyes pass on
Sonnet. Gate 20261109T164910Z-79367.

## Rounds

| Round | Head | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|
| 1 | `1325bf08` | Codex 165 s, 67,700 · fresh-eyes 359 s, 152,661 | 2 / 4 / 5 |
| 2 | `33e6579a` | Codex 160 s, 105,253 | 1 / 3 / 0 |
| 3 | `b417bdca` | Codex 108 s, 58,179 | 0 / 0 / 0 |

Three rounds, 15 findings, 383,793 tokens.

## Round 1

| Seat | Kind | Finding | Disposition |
|---|---|---|---|
| Codex | BUG | A move to another domain has no forwarding on the old host | Fixed: the intake says the old host must forward, this mode does not set it up, and the page document and the go name who does |
| Codex | BUG | `--page` listed 15 queries; the skill says to copy the table | Fixed: up to 100, and "Showing 100 of N" when it cuts; new test fails with the limit at 15 |
| Codex | RISK | Completeness, paging and pages-report claims lack API support | Fixed where we wrote them: the report no longer says quiet days are left out; the skill sends a window still "Not complete" after a week to a hand check; a missing row is "unknown", not zero. Paging past 25,000 rows stays unverified (below) |
| Fresh-eyes | RISK | The completeness text contradicts the real capture (zero-impression days are rows) | Fixed with the text above |
| Fresh-eyes | RISK | Step 9 relies on a pages report the script does not print | Fixed: it points to `gsc_query.py --query` |
| Fresh-eyes | RISK | The pages join ignores URL spellings | Fixed: fold, list unmatched rows |
| Fresh-eyes | NIT ×5 | Step 9 command incomplete; `make_redirects` header lines; old-host sentence; weak test assertion; no capture in the evidence | Fixed; the capture is READ 3 (a live pull equals the fixture's first rows) |

## Round 2

| Seat | Kind | Finding | Disposition |
|---|---|---|---|
| Codex | BUG | `--query` listed 15 pages, so a page at row 16 looked gone | Fixed: one `DRILL_LIMIT` of 100 for both drill-downs, and a "Showing" line; new test fails with the limit at 15 |
| Codex | RISK | Folding assumes the spellings are one page | Fixed: fold only spellings the old site sends to one address |
| Codex | RISK | "No row had no impressions" assumes full coverage | Fixed: "returned no impressions; not proof of zero" |
| Codex | RISK (outside scope) | "Above any catch-all" assumes Cloudflare's order | Fixed: the claim is cut; `check_move.py` tests the redirects after go-live |

## Round 3

No BUG/RISK/NIT findings.

Unverifiable, not counted: that a live pull past 25,000 rows pages as the code assumes (a small site
never reaches it); that Search Console omits queries it anonymises.
