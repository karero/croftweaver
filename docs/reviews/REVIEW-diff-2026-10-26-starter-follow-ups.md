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

## Round 2 — `b4cd1901`, delta from `4248e626` (`--verify` round 1)
`reviewers: codex OK` · `timings: codex 224s (62001 tokens)`
`reviewers: melious OK` · `timings: melious 406s (49832 tokens)` · gate `20261026T111928Z-99804`

Both seats verified every round 1 fix landed.

| id | sev | seat | status | why |
|---|---|---|---|---|
| C4 | BUG | codex | fixed | G6 put the step's keys at dash + 2, so `-   uses:` with its keys aligned after it was a false red. The column now comes from the step's first key; case "\"-   uses:\" with the step's keys aligned after it" fails on the round 2 guard, passes now |
| M5 | RISK | melious | fixed | Accepting `True`/`TRUE` rested on how GitHub and setup-node read booleans, which no one checked; a wrong guess is a false green. G6 now reads only `true`, quoted or not; `True` is a red, which is loud. Case "check-latest: True: red" |
| C5 | RISK | codex | fixed | One sentinel: a real colour equal to it would throw. Now two, readable if either changed (M6 is the same). Chromium probe of the reader, copied verbatim from the spec: `rgb(1, 2, 3)`, `rgb(4, 5, 6)`, transparent, `oklch(…)`, `color(srgb …)` all read; `not-a-colour` throws (round 3 evidence) |
| M6 | NIT | melious | fixed | Same as C5 |
| M7 | NIT | melious | fixed | An inline `with: { … }` is not read: said in G6's comment (a red, not a false green) |
| C6 | — | codex | UNVERIFIABLE, left | setup-node's `check-latest` picks the newest release of the major over a cached one: the action's documented input, not traced in its code here. If false, CI keeps today's behaviour; nothing turns green that was red |
| C7/M8 | — | both | fixed | "WCAG 2.4.13 asks the same" for 2px: not checked. Dropped; the 2px rests on the starter's own ring |
| M9 | NIT | melious | left, outside the diff | `clean.yml`'s 22.12.0 matrix step sets both `node-version` and `node-version-file`; untouched here apart from the added line |

## Round 3 — `32cef515`, delta from `b4cd1901` (`--verify` round 2)
`reviewers: codex OK` · `timings: codex 356s (54253 tokens)`
`reviewers: melious OK` · `timings: melious 441s (41640 tokens)` · gate `20261026T111928Z-99804`

Both seats verified C4 for its own shape, M5, C5/M6, M7 and C7/M8.

| id | sev | seat | status | why |
|---|---|---|---|---|
| C8/M10 | BUG | both | fixed | C4's key column came from the dash line only, so a bare `-` with the keys on the lines below was a false red. The column is now the first key's, on the dash line or the next one; case "a bare \"-\" with the step's keys on the lines below" fails on the round 3 guard, passes now |
| M11 | RISK | melious | fixed | A quoted `"true"` was green on an unchecked claim about how the runner and setup-node read it. Only a bare `true` is read now; quoted is a red. Case "quoted: red" |
| M12 | NIT | melious | fixed | `check-latest:true` (no space) matched; it is not that key in YAML. The match now needs a space; case added |
| M13 | NIT | melious | left | The "none" focus record is the baseline (no CSS appended, see proofs.sh); an explicit `outline: none` was already caught by the old spec's style check, which is unchanged |
| C9 | — | both | UNVERIFIABLE, left | Same as C6: setup-node's `check-latest` resolution not traced in its code. If false, CI behaves as it does today |

## Round 4 — `7d61b2e6`, delta from `32cef515` (`--verify` round 3), `--earned-by yaml-step-layout,setup-node-input`
`reviewers: codex OK` · `timings: codex 372s (38070 tokens)`
`reviewers: melious FAILED (curl exit 28, reply cut off)` · `timings: melious 900s` · gate `20261026T111928Z-99804`

Codex verified M11, M12 and the M13 assertion. GLM 5.3 timed out at 900 s and did not count.

| id | sev | seat | status | why |
|---|---|---|---|---|
| C10 | BUG | codex | fixed by a cut | A dash line holding only a comment took the comment's column as the key column: a false red, the third layout in three rounds. Cut: G6 no longer guesses layouts. It reads one, the starter's (`- uses: actions/setup-node@…`, keys two columns in, `check-latest: true` a direct child of `with:`); any other layout is a red that says "G6 reads only the starter's layout". The named-step, `with:`-first, bare-dash and aligned-key cases now expect that red |
| C11 | — | codex | UNVERIFIABLE, left | `proofs.sh` is in round 1's evidence; C9 as before |
