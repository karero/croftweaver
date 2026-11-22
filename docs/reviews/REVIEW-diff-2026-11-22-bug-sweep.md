# DIFF review — bug sweep of 2026-11-22 (four small BUGLOG rows)

Base `848df35f` (origin/main) · depth: Normal (runtime and shipped code, so not Light) · seats: Codex alone
(REVIEW-RULES; no melious: no High-row topic) and a fresh-eyes sub-agent (Claude Sonnet, read-only) · made by
a session the Croftweaver manager started. Gate id 20261122T224255Z-54046. Artifact per round:
`git diff <base>...HEAD -- . ':(exclude)docs/reviews/'`, with the brief as evidence.

Rows fixed: `check_page_links.py` docstring and `SKILL.md` (a hostless `--site`), the backslash link, the
implied end of `<li>` and `<p>`, and `build-marker.mjs` `isAstroSvg` (`<desc>`, `<title>`, `<metadata>`).
Rows left, with reasons in the PR: the TL9/TL10 concurrency row (no failure names them; noted in the row)
and the `<base>` row (new behaviour, needs a design choice).

| Round | Reviewers | BUG / RISK / NIT | What came back |
|---|---|---|---|
| 1 | Codex; fresh-eyes | 4 / 1 / 2 | a `>` in a quoted attribute and a CDATA `</desc>` beat the regex; a backslash after `?` dropped a valid link; a wrong test comment; the BUGLOG note in the wrong cell; the scanner quadratic on many unclosed elements; a `<` in an attribute value |
| 2 | Codex (`--verify`, base `918175b2`) | 0 / 0 / 0 in scope; 1 outside scope | nested `<metadata>`: the replaced regex had the same hole; BUGLOG row |

Round 1 tokens: Codex 60,233 (223 s), fresh-eyes 103,689 (193 s). Round 2: Codex 70,561 (213 s). Gate total in
the log: 234,483 for the two Codex runs and one logged fresh-eyes seat. Codex alone (REVIEW-RULES); the
script's warning that the standard pair was not met applies.

## Round 1 findings

| Id | Sev | Source | Finding | Status |
|---|---|---|---|---|
| R1-01 | BUG | Codex | `<title data-note=">"/>` before Astro's path and a later `<title>` hid the path | fixed: a left-to-right scanner reads quoted attribute values; refusal test |
| R1-02 | BUG | Codex | `<desc><![CDATA[</desc> d="…"]]></desc>` made a circle icon fail | fixed: `afterElement` skips comments, CDATA and `<?…?>`; acceptance tests |
| R1-03 | BUG | Codex | A backslash after `?` or `#` dropped a valid link | fixed: only the part before them is checked; test for `/p?q=\` and `/p#a\b` |
| R1-04 | BUG | Codex | The backslash test's comment said `/a\p` is `/a/b` | fixed: `/a/p`; the case pins the warning only |
| R1-05 | NIT | Codex | The BUGLOG CI note sat in the Effort cell | fixed |
| R1-06 | RISK | fresh-eyes | The scanner was quadratic: 59 s on 300 KB of unclosed `<desc>` | fixed: an unclosed construct ends the scan, the rest is read as written; a test that fails by timeout on the old scanner |
| R1-07 | NIT | fresh-eyes | A `<` in a quoted attribute value of a drawn tag starts a marker | not fixed: the replaced regex had the same hole; BUGLOG row |

## Round 2 findings

| Id | Sev | Source | Finding | Status |
|---|---|---|---|---|
| R2-01 | BUG (outside scope) | Codex | Nested `<metadata>` ends at the inner closing tag | not fixed: the replaced regex had the same hole, contrived; BUGLOG row |
| R2-02 | UNVERIFIABLE | Codex | A test comment said paths after an unclosed construct "still draw" | fixed: "is still read" |

Both rounds' claims about old runs, mutation runs and CI history were unreproducible for a read-only seat; the
brief holds the commands and outputs, and the PR says what CI covers.
