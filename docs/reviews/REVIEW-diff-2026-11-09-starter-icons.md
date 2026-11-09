# Review trail: diff for the starter's icons (2026-11-09)

Plan: `docs/reviews/SKILL-PLAN-starter-icons.md` (plan trail: `REVIEW-plan-2026-11-09-starter-icons.md`).
Gate: DIFF, Normal, Codex and GLM 5.3 on melious (`independent_review.sh --diff --depth normal`).
From round 2 on, each round reviewed only what changed since the last reviewed head (`--base`),
with the earlier findings passed in (`--verify`) and, from round 3, the runs behind each claim
(`--evidence`). 6 rounds, 12 seat runs, 489,245 reviewer tokens logged by the script (4 runs gave no
figure; the host's own work is not counted).

| Round | Reviewed | Codex | GLM 5.3 | What was done |
|---|---|---|---|---|
| 1 | whole change at `4f45f105` | 4 BUG, 1 RISK | 2 RISK, 3 NIT | The record check no longer throws on a `--brand` that is not `#rrggbb` (a warning); the spec checks a PNG's signature, IHDR and IEND and an ICO frame inside the file; no `KeyError` on a record without a colour value; the glyph-bounds comment. Two rare cases re-sorted to a BUGLOG row; two RISKs refuted by a run. |
| 2 | `cf4458a2..f03a4839` | 3 BUG | 1 BUG, 1 NIT | A plain rerun keeps a letter or colour given with a flag, so the notes name the plain command; the spec walks the PNG chunks and checks where an ICO frame starts. |
| 3 | `f03a4839..6e92cf50` | 4 BUG | out of balance | Chunks end to end with a non-empty IDAT; a frame must be a whole PNG or begin a 40-byte bitmap header; the colour in the script's hints is quoted (`--colour '#rrggbb'`); the plan says only a colour from `--brand` follows a change. |
| 4 | `6e92cf50..2e31571f` | 2 BUG | out of balance | The hand-written PNG and ICO checks were still open to a PNG that inflates to nothing and a bare 40-byte header. Replaced, not patched: the spec has the browser decode the files. |
| 5 | `2e31571f..9909ef0f` | 1 BUG, 1 RISK | out of balance | The 32 px ICO frame is cut out into a one-entry ICO and decoded on its own; a `.png` must start with the PNG signature. |
| 6 | `9909ef0f..99b88c8c` | 1 RISK | out of balance | Refuted by a run (below). No change. |

Rounds 3 to 6: Codex alone, melious out of balance (owner's rule of 2026-10-27: no rerun owed).
Round 2 was run by the planner session; its fixes were committed here as `6e92cf50`.
Rounds 3 to 6 each came with the spec's mutation runs on a real preview build (the bad file in
`public/`, the spec red, the file put back, the spec green).

Round 6's RISK says a truncated PNG that the browser still decodes passes the spec. Run: cutting a
real icon's last 12 bytes (all of IEND) fails the spec; cutting the last 4 or 1 byte (IEND's CRC)
passes, and the browser shows that file in full. A file a visitor sees whole is a working icon, so
nothing to add.

After round 6, CI's `scorecard-skill` job failed: it refuses a tree with uncommitted files, and the
icons step had just written seven. Fixed in the workflow (the step commits the icons). A three-line
change, not sent to a reviewer; CI's rerun is its check.

Not tested (in the PR as well): Node 22.23.4 (only v26.13.0 here); the run-time fallback for a
failed import of `src/config.ts` is covered by the self-test.

The 36 glyphs at 180, 32 and 16 px on a light and a dark tab bar: `docs/reviews/starter-icons-glyph-sheet.png`.
Raw output: the shared notes folder of the 0.35 sweep (outside the repo).

## Artifact 2: the redraw without the outline (2026-11-09)

The maintainer looked at the glyph sheet and answered "No, see notes". In this session he then
approved: "ok to: drop the inner white outline and draw the letter bigger, in all seven files".
`98c145ef` draws no outline, with the letter 1.6 times larger and the stroke 54. At 16 px the
closest pair now differs in 9 pixels (4 before), and at 32 px in 27 (12 before). The tests check
there is no outline, keep the letter 64 units clear of each edge, and require no two glyphs to
look alike at 16 or at 32. The sheet was redrawn as a browser shows `favicon.svg`, with the
corners transparent; the old sheet flattened them, so the tiles looked square. This is a new
artifact under the skill's step 6 ("a redesign is a new artifact with a new count"), reviewed
from `cea8a494` so that `42f0a1af`'s CI change is in it too.

| Round | Reviewed | Codex | GLM 5.3 | What was done |
|---|---|---|---|---|
| 1 | `cea8a494..98c145ef` | 1 RISK | out of balance | The comment said glyphs under the floor "blur into one" in a tab; nothing showed that. Reworded: the floors are regression floors, and the sheet is the check by eye. A wording fix, so no further round. |

Codex alone; melious out of balance (the owner's rule of 2026-10-27: no rerun owed). Run without
`--round`, so the script counts it as a run with no round of gate 20261109T112634Z-44873:
Codex 135 s, 53,040 tokens. Evidence sent with it: `icons-redraw-evidence.md` in the notes folder.
Checked here: `make-icons.test.mjs`, 56 of 56 pass; the brand kit's `TheStartersOwnIcons`, 7 of 7
pass (with `BRAND_KIT_NODE_MODULES` set; without it they skip).
