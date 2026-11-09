# Review trail: diff for the starter's icons (2026-11-09)

Plan: `docs/reviews/SKILL-PLAN-starter-icons.md` (plan trail: `REVIEW-plan-2026-11-09-starter-icons.md`).
Gate: DIFF, Normal, Codex and GLM 5.3 on melious (`independent_review.sh --diff --depth normal`).
Rounds 2 and later reviewed only what changed since the last reviewed head (`--base`), with the
earlier findings passed in (`--verify`).

| Round | Reviewed | Codex | GLM 5.3 | What was done |
|---|---|---|---|---|
| 1 | whole change at `4f45f105` | 4 BUG, 1 RISK | 2 RISK, 3 NIT | The record check no longer throws on a `--brand` that is not `#rrggbb` (a warning); the spec checks PNG signature, IHDR and IEND and an ICO frame inside the file; no `KeyError` on a record without a colour value; the glyph-bounds comment. Two rare cases re-sorted to a BUGLOG row; two RISKs refuted by a run. |
| 2 | `cf4458a2..f03a4839` (round-1 fixes, merge of `main`, README line) | 3 BUG | 1 BUG, 1 NIT | A plain rerun keeps a letter or colour given with a flag, so the notes name the plain command; the spec walks the PNG chunks (IDAT) and checks where an ICO frame starts. |
| 3 | `f03a4839..6e92cf50` (round-2 fixes) | 4 BUG | out of balance | The PNG check takes chunks end to end with none after, and a non-empty IDAT; an ICO frame must be a whole PNG or begin a 40-byte bitmap header; the colour in the script's hints is quoted (`--colour '#rrggbb'`); the plan says only a colour from `--brand` follows a change. |

Round 3: Codex alone, melious out of balance (owner's rule of 2026-10-27: no rerun owed).
Rounds 2 and 3 were run by the planner session and by this session; the round-2 fixes were
written by the planner session and committed here as `6e92cf50`.

Not tested (in the PR as well): Node 22.23.4 (only v26.13.0 here); the run-time fallback for a
failed import of `src/config.ts` is covered by the self-test.

Raw output: the shared notes folder of the 0.35 sweep (outside the repo).
