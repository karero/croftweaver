# Current site and new site: [Site name]

<!-- The relaunch comparison, written beside the pre-launch report when the settings name
the old site ("replaces"). Write it in the owner's language and keep the order. File:
docs/launch/launch-comparison-<YYYY-MM-DD>.md (a second one that day: -2). It holds the old site's paths and the owner's
decisions, nothing else from an inventory. In a public site repo, ask before committing it. -->

**Date:** [YYYY-MM-DD] · **Old site:** [https://www.example.com] · **New site:** [the preview address, or "not deployed yet"]

## Verdict: [🟢 Switch over | 🟡 Switch over once the items below are done | 🔴 Not yet]

[Two or three sentences: what the new site does better, and what still stands in the way.]

## Before launch

- [ ] [Item, with the page or file.]

## Speed: current and new

Measured as `website-qa` §2 does (Lighthouse, or PageSpeed Insights as its fallback); say which.

| Page | Site | Measured at | Performance | FCP | LCP |
|---|---|---|---|---|---|
| Home, mobile | current | [the old site's address] | [not measured: why] | | |
| | new | [the preview, or production at 12a] | [not measured yet: no deployed address] | | |

## E-E-A-T and local signals (an assessment, not a measurement)

| | Current | New | Why |
|---|---|---|---|
| Experience | | | |
| Expertise | | | |
| Authority | not checked: no outside data | not checked: no outside data | |
| Trust | | | |
| Local | | | |

## Open questions for the owner

1. [A decision only the owner can make, with the options.]

## Redirect map for the [N] old addresses

Source of the old addresses: [the inventory's `urls.csv`, complete | the inventory, incomplete because … | the old `sitemap.xml` | the owner's list].

| Old address | Decision | New address | Status |
|---|---|---|---|
| `/old-page` | moved | `/new-page` | ✅ in `public/_redirects` |
| `/kept-page` | keep | `/kept-page` | ✅ in the new build |
| `/gone-page` | let go | — | ✅ |
| `/no-decision` | — | — | ❌ before launch: no decision yet |

## Side by side

| | Current site | New site |
|---|---|---|
| [Topic] | [what it does] | [what it does] |

## What the current site gets wrong

- [Item.]

## What the new site adds

- [Item.]

## What the new site does not have yet

- [Item, and whether it matters for launch.]
