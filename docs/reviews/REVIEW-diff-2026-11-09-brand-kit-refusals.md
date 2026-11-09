# DIFF review: brand-kit refusals (branch `fix/brand-kit-refusals-035`, release 0.35)

Gate: Normal. Why: shipped code that judges untrusted files, plus skill text. Reviewers: Codex
(gpt-6.1-sol) and GLM 5.3 on melious (the second seat); fresh-eyes on a Sonnet subagent.
Plan trail: `SKILL-PLAN-brand-kit-refusals.md` (PLAN gate rounds 1 to 3, red team).
Session: the one that built it ("Croftweaver release 0.35" started it).

## Round 1 (41c323d7), Codex 92k tokens, GLM 95k

| # | Finding | Answer |
|---|---------|--------|
| 1 | BUG HIGH: a failing selector of 24 `\41` escapes took 14.6 s (a hex escape of `{1,6}` digits splits many ways) | Fixed: six digits, or 1 to 5 not followed by a hex digit. Timing test over five runs fails on the old regex (80 s), passes now (2 to 8 ms) |
| 2 | BUG LOW: the BUGLOG refused-exports row said unit opacity is refused | Fixed; the unsupported "editor ... of #498" credit dropped |
| 3 | BUG LOW: grammar text and test docstring said all three opacities must be 1 | Fixed: both name the shape `fill-opacity` 0 exception |
| 4 | RISK: dropping `overflow` assumes the cleaned file is never inline | Checked: the starter uses `favicon.svg` only as `<link rel="icon">` (`Base.astro:148`) and sharp draws the PNGs. Comment names them |
| 5, 6 | NIT: unused variable; BUGLOG "editor" wording | Fixed |
| - | Author's own: the BUGLOG row "refused exports with no way out" was still open | Closed |

## Round 2 (delta since 41c323d7), Codex 57k, GLM 23k: no BUG

RISK (Codex): "as CSS reads it" for the six-digit boundary has no engine comparison. Answered with
one: the sharp render test now draws `.a\000041` and `.a\0000411` from the original and the
cleaned file, and the pictures match. NITs (wording of the BUGLOG row, "non-hex-digit", "optional
blank"): fixed.

## Fresh-eyes (Sonnet subagent, 204k tokens, whole diff): no BUG

- RISK, fixed: a file that leans on its standard DOCTYPE for `xmlns:xlink` was told to copy the whole
  drawing. It now also hears that the declaration is not read (`UNBOUND_PREFIX_STANDARD`), with a test.
- RISK, fixed: `MAX_CLASS` lives in `_css.py` and `_svg.py`; a test holds them equal.
- RISK, accepted: the unbound-prefix message parses the file a second time, so a refused 428 KB file
  with 40,000 attributes took 3.7 s at load average 190. Bounded by the size cap and only on a refusal.
- NIT, fixed: BUGLOG and plan said "five" properties (seven are dropped); two plan lines still said a
  DOCTYPE is refused; a garbled comment; a non-ASCII prefix printed as replacement marks.
- NIT, not done: `SKILL.md` section 7 has no entry for the unbound-prefix refusal; no test for a
  `<clipPath>` child with `fill-opacity="0"` (same output as `fill="none"`).

## Not covered

- The last commit (3d2c4a9e) changes one error sentence, one decode and tests; it had no external
  round. The tests for it ran, and `make check` ran on the final tree.
- Chromium 152 drew 59 original/cleaned pairs the same (max channel difference 0). The probe page
  was a throwaway and is not kept; sharp 0.35.5 is what the repo's render tests use.
- Python 3.9 and an older expat were not run; the code has no syntax newer than 3.9.
