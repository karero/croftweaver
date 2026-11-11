# DIFF gate: fix/move-compare-content-type

Depth: Normal (a fix to the move script, which runs code against a live zone; not Light). Seats:
Codex (effort medium) + GLM 5.3 on melious (`SECOND_SEAT=melious`), fresh-eyes on Claude Sonnet in
round 1. No PLAN gate: a fix that restores intended behaviour (Daniel, 2026-11-10: "Include workers
and 520, 519 and 523 in 0.35 – Ideally I'd like a clean plate"). Gate id 20261111T081035Z-7658.
Every round ran as **Codex alone, melious out of balance** (`Available: 0`; no rerun owed, Daniel,
2026-10-27).

| Round | Diff | Codex | Findings |
|---|---|---|---|
| 1 | 989a6ad1 (base e7e979b2) | 117 s, 68,881 tokens; fresh-eyes 65 s, 94,407 tokens | 3 BUG (codex), 2 RISK + 1 judgment (fresh-eyes) |
| 2 | since 989a6ad1 | 156 s, 34,921 tokens | 1 BUG |
| 3 | since 8cd92f86 | 88 s, 50,539 tokens | none in scope; 1 outside scope, fixed |
| 4 | since 8cd92f86 | 77 s, 27,361 tokens | none |

Round 4 needed `--earned-by parameter-handling`: rounds 1 to 3 each found a parameter case the
parser or a guard let through.

| Id | Sev | Source | Where | Finding | Status | Fix / reason |
|---|---|---|---|---|---|---|
| F1 | BUG | codex | `contentTypeKnown` | A quoted parameter (`note="a; b"`) was split on `;` and trimmed, so a changed value was excused | fixed | Any `"` in either value is refused (unknown); no real header sends one |
| F2 | BUG | codex | `contentTypeKnown` | `application/javascript; charset=utf-8` to `text/javascript; charset=utf-8` was unknown | fixed | The JS rule keeps unchanged parameters, or a dropped utf-8 charset |
| F3 | BUG | codex | `UTF8` | The optional quotes matched `charset="utf-8` | fixed | The pattern takes no quotes |
| F4 | RISK | fresh-eyes | `contentTypeKnown` | A second charset parameter took over silently | fixed | More than one charset parameter is refused |
| F5 | judgment | fresh-eyes | PR text | The charset drop is excused for any media type, but a client then guesses the encoding | disclosed | Said in the PR: it is the difference the capture shows; owners may want to set the charset in `_headers` |
| F6 | BUG | codex r2 | `contentTypeKnown` | The lost-header redirect return came before the guards | fixed | Guards first; redirect tests with a quote, a malformed quote and a second charset |
| F7 | BUG | codex r3, outside scope | `contentTypeKnown` | A redirect losing `charset=iso-8859-1` or `foo=bar` was excused | fixed | The redirect exception needs no parameters, or only utf-8 charset ones |
| F8 | NIT | fresh-eyes | tests | A difference only in case or spacing (`UTF-8` against `utf-8`) is refused | not changed | A false refusal is loud and safe; no capture shows it |

Mutation check (mutation-check skill, throwaway copy): 10 mutations of the fix; 3 survived (any type
to JS, a same value excused, an added header excused), three assertions were added and all 10 were
then killed. The guards added in rounds 1 to 3 (quotes, second charset, the JS parameters, the utf-8
pattern, guard order, redirect parameters) were each reverted once and each failed a test.
