# DIFF review: a generator tag in every starter site

Plan: `docs/reviews/SKILL-PLAN-generator-tag.md` (PLAN gate clean: 4 rounds, 5 findings;
trail `REVIEW-plan-2026-10-27-generator-tag.md`). The maintainer's go to build, 2026-10-27: "Yes, build the
generator tag as planned". Gate: independent-review DIFF, depth Normal (skill text and starter
code that ship to users). Seats: Codex and GLM 5.3 on melious, both counted in every round.

| Round | Findings | Disposition |
|---|---|---|
| 1 | BUG: the test's pattern accepted a commented-out tag and a tag with other content. RISK: an owner's own generator tag failed the test. NITs: switch read two ways; loose name pattern; README line after the message | all fixed |
| 2 | BUG: text matching still counted a tag quoted in another attribute or a script. RISKs: spaces around `=`; unquoted attributes; (two seats) README-first order could leave the owner never told. NIT: tags in pre/code/script | fixed by reading each built page with the browser's DOMParser; tell first, then record (round 1's NIT re-sorted: told twice is harmless, never told is not) |
| 3 | NIT: the test comment's "quoted examples" claim did not hold for `<noscript>` | fixed: the comment no longer claims it |

Checks before review (quoted output in the PR): old site with main's `Base.astro` and
`config.ts` passes; the tag removed, a layout ignoring the switch, a tag only in a comment, and a
tag only quoted inside another tag and a script all fail; spaces around `=` and an owner's extra
generator tag pass; switch off passes; `npm run check` 0 errors in every case. Full starter suite
115 passed, 1 skipped (built-in). `make check` exit 0 after rebasing onto main (#435).

Totals: 3 rounds, 12 findings (2 BUG, 5 RISK, 5 NIT), all fixed or re-sorted. Tokens (script
log): 140,151 for rounds 1-3 (Codex 46,477 + 29,734 + 35,436; melious 12,048 + 8,804 + 7,652).
