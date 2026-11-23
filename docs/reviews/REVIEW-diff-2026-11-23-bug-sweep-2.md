# DIFF review — bug sweep 2 of 2026-11-23 (five small BUGLOG rows)

Base `65d46dfc` (origin/main) · depth: Normal (runtime and shipped code, so not Light) · seats: Codex alone
(REVIEW-RULES; no melious: no High-row topic) and a fresh-eyes sub-agent (Claude Sonnet, read-only) · made by a
sub-agent of the Croftweaver manager's session. Artifact per round: the diff against the base (round 1) or since the
last reviewed head (rounds 2 and 3), with the brief as evidence.

Rows fixed: `move-to-workers.mjs` status line (2026-11-22), the second G1 test (2026-11-16), `check_external_links.sh`
`SITE_HOST`, the `icons.spec.ts` PNG sizes, `check_ship_push.sh` L3f (and L3d, same gap). Row left: `_install.py`
`regenerate_cards()` (the generator's comment says the last line is meant; the row says "if wanted": the maintainer's call).

| Round | Reviewers | BUG / RISK / NIT | What came back |
|---|---|---|---|
| 1 | Codex (base `65d46dfc`, head `b0cd912e`); fresh-eyes | 2 / 1 / 0 (Codex); 0 / 3 / 5 (fresh-eyes) | IPv6 host cut at its first colon; L3d/L3f matched a prefix of the id; G1 timing; fresh-eyes: a port in `site:`, the G1 fix unproven for a pid not held by a child, no size check for `<link rel="icon">` PNGs |
| 2 | Codex (`--verify`, base `b0cd912e`, head `1e159b6e`) | 0 / 1 / 0 | the G1 timing risk again |
| 3 | Codex (`--verify`, base `1e159b6e`, head `70f7472a`) | 0 / 1 / 0 | a child still tries the lock after its 60 s wait ends |

Tokens and time: round 1 Codex 66,865 (204 s); round 2 Codex 32,903 (112 s); round 3 Codex 28,763 (66 s); fresh-eyes
122,058 tokens (52 s). Codex alone (REVIEW-RULES); the script's warning that the standard pair was not met applies.

## Findings

| Id | Sev | Source | Finding | Status |
|---|---|---|---|---|
| R1-01 | BUG | Codex | An IPv6 `site:` host was cut at its first colon, so another IPv6 host counted as the site's own | fixed: a bracketed host is kept whole in `SITE_HOST` and the filter; a test case |
| R1-02 | BUG | Codex | `has "    $m"` for L3d/L3f passes a longer id that starts with `$m` | fixed: `verdict_has` matches a whole line (`grep -qxF`); checked by hand against the real ship.sh |
| R1-03 | RISK | Codex | The G1 rewrite races the 3 s start time on a slow machine | fixed in round 3: the children wait for a start file the parent writes after the rewrite |
| R1-04 | RISK | fresh-eyes | A `:port` in `site:` made own links reach the external report | fixed: the port is dropped from `SITE_HOST`; the test uses a port |
| R1-05 | RISK | fresh-eyes | The G1 fix covers only a pid held by one of the six children | not fixed: the row says a later Windows failure reopens it |
| R1-06 | RISK | fresh-eyes | No `sizes` check for a PNG linked by `<link rel="icon">` | not fixed: no such PNG is in `ICONS`; the earlier assertion requires the path to be linked |
| R1-07 | NIT | fresh-eyes | BUGLOG row text "five or six children" | fixed: "the six children" |
| R1-08 | NIT | fresh-eyes | The row names a harness branch name | not fixed: the branch name is the one the manager pushes or renames |
| R3-01 | RISK | Codex | A child tries the lock when its 60 s wait ends without `go` | not fixed: it needs a parent stalled for a minute; re-sorted: rare |

Other fresh-eyes NITs (`?`/`#` after the host, a host that only contains the site host, the old `verdict_lacks`
asymmetry) are noted and not changed: the twin script has the first, and the others need a later change to matter.

Claims about the Windows logs, the mutation runs and the suite results were UNVERIFIABLE for a read-only seat; the brief
holds the commands and outputs. Round 3 ended with one RISK, sorted as rare.
