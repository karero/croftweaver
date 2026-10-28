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

## Round 5 — `91ba6fc3`, delta from `7d61b2e6` (`--verify` round 4), `--earned-by yaml-step-layout --cut "G6's layout guessing removed…"`
`reviewers: codex OK` · `timings: codex 182s (45697 tokens)`
`reviewers: melious OK` · `timings: melious 706s (50192 tokens)` · gate `20261026T111928Z-99804`

| id | sev | seat | status | why |
|---|---|---|---|---|
| C12 | BUG | codex | fixed by a cut | `with:` at column 8, a key at 9 and `check-latest: true` at 10 passed, though YAML nests it under that key. Case "check-latest at column 10 under a key at column 9" passes the round 5 guard, is red now |
| C13 | BUG | codex | fixed by a cut | A second step `- uses: "actions/setup-node@v7"`, quoted, was never found, so it stayed green without check-latest. Case "a second, quoted setup-node step appended" passes the round 5 guard, is red now |
| M14 | NIT | melious | moot | "says so" overclaimed for a `with:` styled otherwise; that code is gone |

The cut, on the maintainer's decision relayed from the "Croftweaver feature-planning" session ("Make G6 a literal check: compare the starter's setup-node step byte for byte with the expected block, red with a clear message otherwise. One more review round on that, then push, PR and merge once clean."): G6 parses no YAML. `EXPECTED_SETUP_NODE` in `check_node_floor.sh` holds the step's text; ci.yml must hold it once, starting a line, followed by the next step or the end, and name `setup-node` nowhere else. The red says to change the constant together with the step. The layout cases are replaced by: the shipped starter passes, and eleven changed texts are red (both cases above among them, and a v8 bump without the constant). The G4 case that quotes `node-version: '24'` now expects G4 quiet and G6 red.

## Round 6 — `c285f657`, delta from `91ba6fc3` (`--verify` round 5), `--earned-by yaml-step-layout --cut "G6 parses no YAML…"`
`reviewers: codex OK` · `timings: codex 180s (38550 tokens)` — "No BUG/RISK/NIT findings."
`reviewers: melious OK` · `timings: melious 229s (22039 tokens)` · gate `20261026T111928Z-99804`

No BUG, no RISK. The gate is clean at `c285f657`.

| id | sev | seat | status | why |
|---|---|---|---|---|
| M15 | NIT | melious | left | `ci.indexOf(EXPECTED_SETUP_NODE, at + 1)` can never decide the result (a second copy also fails the one-mention check); harmless, left to avoid a code change after the last round |
| M16 | NIT | melious | left | A blank or comment line after the step is a red whose message says only "not byte for byte". The message is a string in the code, so changing it after the last round is not a wording fix (wording pass W2); the header now says what the check compares |
| M17 | NIT | melious | fixed (wording) | "as a whole step" claimed more than the check does; the header now says "starting a line and followed by the next step or the end" |

Totals, rounds 1–6: 6 rounds, 44 distinct findings (6 BUG, 9 RISK, 23 NIT, 6 UNVERIFIABLE notes); seat tokens logged 437,553 (codex 300,230, melious 197,881 counting round 4's timed-out run as 0) plus fresh-eyes 120,040.

## Wording pass — `8f3ee2ef`, prose since `c285f657` plus the BUGLOG row, `--wording-pass --seat codex`
`reviewers: codex OK` · `timings: codex 129s (35249 tokens)`

| id | sev | seat | status | why |
|---|---|---|---|---|
| W1 | BUG | codex | fixed | The BUGLOG row said "against the background it is drawn on"; the test reads solid background colours only. Now "the solid background colour behind it … (background images and gradients are not read)", and "stays green" names the `--bg` colours too |
| W2 | BUG | codex | fixed | The red message's text is a JavaScript string, not prose; reverted to the round 6 text. `check_node_floor.sh` now differs from `c285f657` in comment lines only |
| W3 | RISK | codex | refuted, with a source | What `check-latest` does: setup-node's own documentation (https://github.com/actions/setup-node/blob/main/docs/advanced-usage.md, read 2026-10-26): with `check-latest: true` "the action first checks if the cached version is the latest one", and downloads the newest when it is not; with `false` it takes a cached semver match first |

## Wording pass, second read — `0a352836`, delta from `8f3ee2ef`
`reviewers: codex OK` · `timings: codex 354s (46572 tokens)`

| id | sev | seat | status | why |
|---|---|---|---|---|
| W4 | BUG | codex | refuted | The hunk is W2's revert back to the code round 6 reviewed: `git diff c285f657..HEAD -- scripts/check_node_floor.sh` changes 0 lines outside comments |
| W5 | RISK | codex | refuted | W3 again; the action's own documentation, cited above, is the support. If it were wrong, CI would behave as it does today, not worse |

Since `c285f657`, the last head both seats reviewed clean, only comments, the BUGLOG row and this trail changed.
