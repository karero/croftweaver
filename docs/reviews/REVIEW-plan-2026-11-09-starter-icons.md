# Review trail: plan for the starter's icons (2026-11-09)

Plan: `docs/reviews/SKILL-PLAN-starter-icons.md`. Gate: PLAN, Normal, Codex and GLM 5.3 on
melious (`independent_review.sh --plan --depth normal`). 4 rounds, 10 seat runs, 459,959 reviewer
tokens logged by the script (the host's own work not counted).

| Round | Codex | GLM 5.3 | What was done |
|---|---|---|---|
| 1 | 2 BUG, 3 RISK | 2 RISK, 5 NIT | Command moved after the name is set (README step 4); record keeps old and new hashes during the renames; a stop tested at each point; CI jobs make the icons before the suite; the seven paths written in the test; the record says where letter and colour came from, so an override does not warn for ever; NITs fixed. |
| 2 | 1 BUG, 1 RISK | 5 RISK, 3 NIT | Each record written to a temporary file and renamed; the test follows the page's manifest link; `sharp` checked in the lockfile; Astro-logo hashes replaced by `--setup` (CI never runs create-astro, so a new logo would stop every setup unseen); brand-kit sizes checked against the pins; sites built from `tab-icon.md` lack `images/logo.png`, so whats-new says to copy it; NITs fixed. |
| 3 | 1 BUG | 3 RISK, 3 NIT | The brand kit's first line has three forms: match their shared start; `--setup` only on a fresh-looking site; whats-new note per kind of site; `tab-icon.md` sizes stated; the `Example` NIT refuted in part (the starter's own value; S6 is tested on the shipped `config.ts`). |
| 4 | clean | 1 RISK, 3 NIT | Fixed after the round, not reviewed again: the brand kit's S9 test also asserts the seven sizes; `--setup` needs `favicon.svg` to exist; temporary files outside `public/`; 16 pixels named as checked by eye only. The DIFF gate reads these with the code. |

Round 4 was earned by round 3's BUG and RISKs (`--earned-by file-ownership,setup-overwrite,whats-new-advice`).
Raw output: the shared notes folder of the 0.35 sweep (outside the repo).
