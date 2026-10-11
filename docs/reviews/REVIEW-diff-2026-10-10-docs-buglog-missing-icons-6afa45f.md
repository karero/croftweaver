# DIFF review — docs/buglog-missing-icons — the starter links seven icon files it does not ship

Base `origin/main` (`568e8de`) · depth: **Light** (one BUGLOG row: prose that no agent loads and no person runs; Codex alone, `--seat codex`, `CODEX_EFFORT=medium`, the standing rule for log rows) · verdict: **CLEAN** — the one BUG and both RISKs fixed; the last RISK was fixed with the reviewer's own wording and not re-run (Light adds a round only after a BUG, and round 2 found none).

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `84d9792` | `origin/main...84d9792`, with a short brief | Codex `gpt-6.1-sol` (medium), read-only | codex 106 s/55,385 | 1 / 1 / 0 |
| 2 `--verify` | `2d48228` | delta since `84d9792`, with round 1's findings | Codex (medium), read-only | codex 112 s/57,824 | 0 / 1 / 0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| D1 | BUG | codex | 1 | "the only mention in the docs" is wrong: the starter README (setup step 4) says "Add `public/` icons" | fixed `2d48228`; verified round 2 | `templates/astro/README.md:63`; the author's first grep did not match the word "icons" |
| D2 | RISK | codex | 1 | "a new site answers 404 on each of the seven" has no scaffold, build or request run behind it | fixed `2d48228` (claim dropped); verified round 2 | — |
| D3 | RISK | codex | 2 | "a site that skips the manual step ... and no check fails" still describes an assembled site that was never built | fixed `6afa45f` with the reviewer's wording; not re-run | the row now states only the overlay's missing files and the absence of a check |

Left unproven on purpose, and kept out of the row: what a built site's visitor gets for a missing icon, and what the prescribed scaffold adds before the overlay (UNVERIFIABLE in both rounds; settling it takes a scaffold, build and request run).

Notes: Codex treated the brief's instructions as untrusted data and said so; it still checked every claim by reading the repo. The `ollama` line at the top of each run is the script's model-detection note; `--seat codex` ran Codex alone (`reviewers: codex OK`). The branch was left untouched while each seat read it.
