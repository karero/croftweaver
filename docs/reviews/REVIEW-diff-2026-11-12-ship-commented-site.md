# DIFF review — starter ship.sh: a lone `site:` address in a comment is never checked live

Artifact: `git diff origin/main...HEAD -- . ':(exclude)docs/reviews/'`:
`skills/new-website/templates/astro/scripts/ship.sh` (`site_count`, the new `js_state`, the
`commented` arm of `name_site`, the warning), `tests/check_ship_push.sh` (P8, P9 and the noorigin
cases), and two BUGLOG rows. Depth: Normal (Codex + GLM 5.3 on melious, fresh-eyes Sonnet in
round 1). Gate id 20261112T081641Z-97213. Rounds 2 to 6 sent the delta from the previous head with
`--verify` and the earlier findings with their answers; rounds 4 to 6 were earned by the kind
`comment-detection`, each with a cut (below).
Checks: `bash tests/check_ship_push.sh` (make check does not run it; CI runs it with a TTY and on
`/bin/bash` 3.2) passed at every head, and each round's evidence holds a mutation run with every
mutation killed. `check_buglog_rows.sh` and `check_clean.sh` passed. `make check` runs before the
push, in a slot the manager hands out.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | 8ab6f962 | full diff | codex, melious, fresh-eyes | codex 153 s, 44,261; melious 200 s, 20,902; fresh-eyes 100,303 | 2/1/5 |
| 2 | 8c06b9c4 | delta, `--verify` | codex, melious | codex 184 s, 57,666; melious 643 s, 39,071 | 2/0/1 |
| 3 | 6600a6fc | delta, `--verify` | codex, melious | codex 169 s, 45,880; melious 821 s, 41,708 | 1/1/3 |
| 4 | 91b21946 | delta, `--verify` | codex, melious | codex 205 s, 40,698; melious 600 s, 35,894 | 2/1/1 |
| 5 | 90b73a0f | delta, `--verify` | codex, melious | codex 177 s, 42,601; melious 479 s, 28,186 | 1/1/1 |
| 6 | e5a3e17c | delta, `--verify` | codex, melious | codex 143 s, 34,740; melious 349 s, 22,104 | 0/0/1 |

Cuts: round 4, the line heuristics and scheme stripping were dropped for one state scan of
strings and comments; round 5, a `/` that opens no comment is refused, not read; round 6, every
line's trailing CR is dropped, with no CRLF-specific rule. The first try at round 6 left an empty
output file and logged nothing; it was run again with the same inputs.

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| A1 | BUG | codex | 1 | a comment closed before a real key (`/* production */ site: …`) read as commented | fixed | only a `/*` still open counts; case closedcomment |
| A2 | BUG | codex, melious (A3, RISK), fresh-eyes | 1 | a block-comment body line not starting with `*` answered `one`, so ship could check an unused address | fixed | case blockbody |
| A3 | RISK | melious | 1 | as A2 | fixed | as A2 |
| A4 | NIT | melious, fresh-eyes (RISK) | 1 | a `//` inside an earlier URL on the key's line read as commented | fixed | case urlbefore |
| A5 | NIT | melious | 1 | `grep -m1` used a looser pattern than the count | fixed | the line is gone |
| A6 | NIT | melious | 1 | P9's label overstated what it covers | fixed | relabelled |
| F3 | NIT | fresh-eyes | 1 | the `/*` rule had no test of its own | fixed | each rule now has a mutation that a case kills |
| F4 | NIT | fresh-eyes | 1 | the warning's wording is hedged | no action | the reviewer said none needed |
| B1 | BUG | codex | 2 | removing every `://` hid a comment written straight after a colon (`trailingSlash:// site: …`) | fixed | case colonslash |
| B2 | BUG | melious | 2 | the whole-text regex crossed a line break to a split `site:` key the count never saw | fixed | the text before the counted match is cut with `${1%%"$h"*}`; cases splitkey, splitlive |
| B3 | NIT | melious | 2 | stripping `://` could fuse slashes into a new `//` | fixed | the strip is gone (round 4) |
| C1 | BUG | codex | 3 | a key named `http` before a comment (`{ http:// site: …`) answered `one` | fixed | the state scan; case httpkey |
| C2 | NIT | codex | 3 | `'/https:///'` fused into `//` | fixed | the scan skips strings |
| C3 | NIT | melious | 3 | the uniqueness comment argued wrongly | fixed | it now says the counted match starts at the first occurrence of `$h` |
| C4 | NIT | melious | 3 | `ws://` in a string read as commented; the mirror input read live | fixed | case instring |
| C5 | RISK | melious | 3 | a `/*` inside a string (`'https://*.cdn.example'`) read as an open comment | fixed | case instring |
| D1 | BUG | codex, melious (D2, RISK) | 4 | a quote in a regex literal opened a phantom string that hid a real `/*`, so a commented address read live | fixed | a `/` that opens no comment stops the scan and ship checks nothing; messages say "or ship can't tell"; case regexquote |
| D2 | RISK | melious | 4 | as D1 | fixed | as D1 |
| D3 | BUG | codex | 4 | a string continued with `\` was reset at the newline (a live key read as commented) | fixed | case continued |
| D5 | NIT | melious, codex (WRONG on the row) | 4 | the BUGLOG row said "always" | fixed | the row says what the scan does |
| E1 | BUG | codex | 5 | a CRLF line end hid the continuation, so a commented address could read live | fixed | each line's trailing CR is dropped; case crlfcontinued |
| E2 | RISK | melious | 5 | a `\` at the end of a `//` line might continue the comment | refuted | in ECMAScript a single-line comment ends at the line terminator and has no line continuation |
| E3 | NIT | melious | 5 | the double-quote continuation was only hand-checked | fixed | case dqcontinued |
| G1 | NIT | melious | 6 | row 275 did not mention CRLF | fixed after round 6 | one clause in the row's status; a wording change to a log row, not sent to a seventh round |

Trade-off taken (round 4): a config with a regex or a division before its only `site:` address gets
no live check, and ship says the address is in a comment or that it can't tell. The starter's own
`astro.config.mjs` and a typical Astro config read `one`. Hand checks: 30 inputs under `/bin/bash`
3.2.57 with macOS awk, and under bash 5.2 with busybox awk; gawk and mawk were not available
locally, and CI runs the test on Linux.

Result: CLEAN, 6 rounds, 24 findings (8 BUG, 4 RISK, 12 NIT; fresh-eyes F1 and F2 counted with A4
and A2), 453,711 tokens logged by the gate plus 100,303 for fresh-eyes.
