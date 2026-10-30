# DIFF review: the tab icon recipe (a tile with an inner outline)

Plan: reviewed in the maintainer's private feature notes (PLAN gate clean: 4 rounds and a final
full read, 23 findings, all fixed). Gate: independent-review DIFF, depth Normal (`SKILL.md` text
agents load, and a reference with commands a person runs). Seats: Codex + GLM 5.3 on melious;
fresh-eyes (Claude Sonnet, no shared context) in round 1.

Evidence each round: the recipe run once from its own text on an "A" on `#1f5c3a` (tool
versions, `magick identify`, corner pixels, the maskable icon's farthest white pixel at 0.345
of the side), the W3C App Manifest's safe-zone sentence (section 2.3), and the reference's test
file run in a scratch copy of a client site: calibration scores, and a failing run for each
break (a stale 192 file, a `prefers-color-scheme` rule, a tile one shade off, an escaped rule
hiding only the crossbar) and a green run after the site's brand colour changed.

| Round | Findings | Disposition |
|---|---|---|
| 1 (Codex; melious out of balance, no rerun owed; fresh-eyes) | Codex and fresh-eyes: 1 BUG (the reference said a colours-only run leaves the hand-built icon "with a note"; `_install.py` adds the note only when a page background changes). Codex: 1 BUG, fresh-eyes: 1 RISK, the same one (§8a said "page backgrounds only"; `backgrounds()` also tries white and black). Fresh-eyes: 2 NIT (a long line; the 1.88 and 1.17 figures cited "one review") | fixed: the reference and §8a say the note comes only when a page background changes, and to redraw the icon by hand after any run that changes the brand colour; "the page backgrounds, then white and black, never a tab bar"; re-wrapped; the figures say a reviewer measured them with `rsvg-convert` |
| 2 (Codex, verifying round 1; melious out of balance) | round 1's fixes confirmed. Outside scope: 1 BUG (the older §8 line "left as it is, with a note" makes the same promise) | fixed here, since it is the file this change edits: "a note says so only when a page background changes" |
| 3 (Codex, verifying round 2; melious out of balance) | none | clean |
| wording pass (Codex alone, this trail; main merged in, touching none of this change's files) | 1 BUG (the 157 skipped tests are not all icon drawing: Pillow also gates CSS colour names and share cards) | fixed: the line names the three kinds |

Checks before round 1: `make check` exit 0 (warnings only: `website-brand-kit/SKILL.md` 546
lines and `new-website/SKILL.md` 980 lines, over the 500-line soft budget, and the brand kit's
description at 953 characters, near its limit; all three predate this change); `make test-brand-kit`
1082 tests OK, 157 skipped (the tests that need `sharp` or Pillow, neither installed for this
run: icon drawing, CSS colour names, share cards).
After main was merged in: `make check` exit 0 on `284e6c55` ("all checks passed"; the brand
kit's `SKILL.md` now 549 lines).

Totals: 3 rounds and a wording pass, 6 findings (4 BUG counted once each, 2 NIT), all fixed. Codex alone counted
every round: the GLM 5.3 seat on melious failed with an empty balance, and by the maintainer's
rule of 2026-10-27 each round stands on Codex. Tokens: Codex 134,320 in the rounds and
77,187 in the wording pass and its first confirmation (script log); fresh-eyes 108,983.
