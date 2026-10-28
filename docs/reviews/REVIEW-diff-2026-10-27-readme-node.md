# DIFF review — README: installing and building have different Node minimums

Branch `docs/readme-node-requirements`. Depth: **Normal**, not Light: the diff changes the Node
prerequisite of a quick-start step a person follows, and when unsure the rule says deeper. No
code, guard or script changes. Seats: Codex and GLM 5.3 on melious, one command. Evidence file
sent with `--evidence`: the installer's and the starter's `engines`, `.nvmrc`, SETUP.md:84-89,
SKILL.md:496-500, and why no starter version is copied into the README (check_node_floor.sh
guards the versions in four docs, not the root README).

From the follow-up growth audit of 27 October 2026: "Clarify that installation's Node
requirement and building a site's Node requirement differ."

## Round 1 — `9f4cd2f6`, base `09cc683a`
`codex OK` 167s (55,698 tokens) · `melious FAILED` 2s (out of balance)

Codex alone. melious out of balance: by the owner's rule (2026-10-27) Codex alone is enough
for this round, and no rerun of melious is owed.

Codex: CLEAN. It verified each claim against the files: the installer floor (package.json and
the runtime check in index.mjs), the starter range and `.nvmrc`, that every starter version is
above the installer floor, SETUP.md naming the versions, SKILL.md's stop on EBADENGINE, that
install.sh and index.mjs run no Node or other program, and that the floor guard does not read
either README (it ran `check_node_floor.sh`, which passed). No findings.

Stop: round 1 has no BUG and no RISK. Gate closed on `9f4cd2f6`.
