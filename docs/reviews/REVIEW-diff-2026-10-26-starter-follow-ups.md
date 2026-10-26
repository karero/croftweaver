# DIFF review — starter follow-ups before 0.34: setup-node check-latest, a visible focus ring

Branch `claude/starter-follow-ups-034-ca33ed`. Depth: **Normal** (the starter's shipped tests and CI, and the
logic of a guard script). Seats run as separate commands with the same `--round`: codex, then GLM 5.3 on
melious; fresh-eyes (Sonnet subagent) in round 1. `docs/BUGLOG.md` (the release-notes row) is record prose
and left out of the round diffs.

Not changed, with evidence: the third follow-up, "tables.spec.ts measures without opening `<details>`". In the
starter's Chromium a table inside a closed `<details>` is laid out and measured exactly as in an open one
(same height, line boxes and scroll width). On origin/main's spec, a too-wide figures table and a word split
across lines, each inside a closed `<details>` on `/privacy`, both turned the scan red (records
`details-old-closed-*` in the round 1 evidence). No failing test could be written, so the spec is left alone.

## Round 1 — `4248e626`, base `1a90b1ae`
`reviewers: codex OK` · `timings: codex 139s (61661 tokens)` · gate `20261026T111644Z-88019`
`reviewers: melious OK` · `timings: melious 267s (34216 tokens)` · gate `20261026T111928Z-99804`
fresh-eyes (Sonnet subagent): 120,040 tokens, 75 s

| id | sev | seat | status | why |
|---|---|---|---|---|
| C1 | BUG | codex | fixed | G6 took `check-latest: true` from anywhere in the step (its `env:` too). Now only a direct child of the step's `with:`; case "under the same step's env:" fails on the round-1 guard, passes now |
| C2 | RISK | codex | fixed | G6 scanned only after `uses:`, so `with:` written first was a false red. It now reads the whole step; case "with: written before uses:" |
| F1 | RISK | fresh-eyes | fixed | Only 3 of 18 toolkit setup-node steps that read the starter's `.nvmrc` had `check-latest`; several run `npm ci` in the starter. Now all 18. The 18/20/22 matrix step reads no `.nvmrc` and installs no starter, so it is left. Nothing guards the toolkit's own workflows (G6 reads only files that ship in the zip) |
| F2 | RISK | fresh-eyes | fixed | "one engines refuses": npm only warns (EBADENGINE, exit 0). Reworded. The 24.21.0 run is from the sites session's notes ("GitHub served cached 24.21.0"), quoted in round 2's evidence |
| M1 | NIT | melious | fixed | Same as C1 |
| M2 | NIT | melious | fixed | `check-latest: True` or `"true"` was a false red; accepted now, case added |
| M3 | NIT | melious | fixed | The background walk started at the link, but a ring with offset ≥ 0 is drawn outside it; it now starts at the link only when the offset is negative (the starter's table links: -2px) |
| M4/F5 | NIT | both | fixed | A colour the canvas cannot read kept the previous fill; it now throws |
| F3 | NIT | fresh-eyes | fixed | Same as C1 |
| F4 | NIT | fresh-eyes | fixed | The G6 case pinned `ci.yml:127`; it now checks the message and the file name |
| F6 | NIT | fresh-eyes | fixed | Background images and gradients are not read: said in the test's comment |
| C3 | — | codex | fixed | UNVERIFIABLE: WCAG 1.4.11 sets no width. The comment now cites the starter's own 2px ring and 2.4.13 for the width, 1.4.11 for 3:1 |
