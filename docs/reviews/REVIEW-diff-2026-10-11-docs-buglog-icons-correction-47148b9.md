# DIFF review — docs/buglog-icons-correction — the icon row, now that the scaffold's own icons are known

Base `origin/main` (`0af174e`) · depth: **Light** (one existing BUGLOG row, prose that no agent loads and no person runs; Codex alone, `--seat codex`, `CODEX_EFFORT=medium`, the standing rule for log rows) · verdict: **CLEAN** — no BUG; both RISKs fixed with the reviewer's own wording and not re-run (Light adds a round only after a BUG).

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `794d30c` | `origin/main...794d30c`, with a short brief | Codex `gpt-6.1-sol` (medium), read-only | codex 132 s/56,333 | 0 / 2 / 0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| E1 | RISK | codex | 1 | 'a scaffolded site holds two … lacks five' generalises one create-astro 5.2.6 run to the skill's `astro@latest` workflow | fixed `47148b9`: the inventory is scoped to the 2026-10-10 run and says a later version may differ | `skills/new-website/SKILL.md:282` |
| E2 | RISK | codex | 1 | 'stay the site's tab icon' is an untried browser claim; the row also called both icons the Astro logo although only the SVG was read | fixed `47148b9`: the two files stay in `public/` and the pages still link them; the `.ico` is said to be unopened | — |

Left unproven and kept out of the row: what a built scaffold's visitor sees as a tab icon, and the scratch run itself (create-astro's version, the byte counts, the generated links), which the reviewer could not rerun without network. Codex marked both UNVERIFIABLE and they are stated as the author's record in the row. Checked CLEAN: the seven references, the overlay's five public files, the scaffold instruction at `SKILL.md:282-285` with no deletion step, the README and checklist quotations, the absence of an existence check, and the table's seven cells.
