# DIFF review — `$0` amounts in three skills

Artifact: `git diff origin/main...HEAD -- . ':(exclude)docs/reviews/'`: five lines in
`skills/ai-seo/SKILL.md`, `skills/search-console-insights/SKILL.md` and
`skills/website-team-setup/SKILL.md` that wrote an amount as `$0…`, and one BUGLOG row. Depth:
Normal (Codex + GLM 5.3 on melious): a SKILL.md is Never Light. Evidence for every round: the
ai-seo skill as it loaded with arguments, and a probe skill loaded with three arguments and with
none (quoted in the BUGLOG row). Checks: `make check` passed on a6f021fe; the final head runs it
in a slot the 0.35 manager hands out.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | a6f021fe | ai-seo commit only | codex (melious FAILED: reply cut off, curl exit 56, after 1172 s; a first run sent the second seat to glm-5.3-flash on ollama, which does not count) | codex 89 s, 26,725 | 0/0/0 |
| 2 | 61e93825 | full diff | codex alone (melious FAILED: the model stopped mid-stream, HTTP 200, after 462 s) | codex 104 s, 38,937 | 1/2/0 |
| 3 | b07cc512 | delta, `--verify` | codex, melious | codex 137 s, 31,723; melious 165 s, 12,145 | 1/0/1 |
| 4 | ac59bf63 | delta, `--verify`, earned by buglog-row-claims, cut | codex, melious | codex 69 s, 25,503; melious 71 s, 8,078 | 0/0/1 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| C1 | BUG | codex | 2 | the BUGLOG row said nothing changed with no arguments, but `$ARGUMENTS` became empty | fixed in b07cc512 | the row now says so |
| C2 | RISK | codex | 2 | the row stated a general `$N` rule the probe cannot show for `$10` or `$29` | fixed in b07cc512 | the row lists only what the probe showed, names what was not checked, and its guard covers any `$` and digit; a 30-argument probe could not run because the loader did not register a new skill mid-session |
| C3 | RISK | codex | 2 | the website-team-setup zero-budget claim has no followed source | outside scope | the diff changes only how the amount is written; the claim and its links are unchanged |
| M1 | BUG | melious | 3 | the row's new opening sentence still stated a rule for every `$N`, which the probe disproves | cut in ac59bf63 | the sentence is gone; the row opens with what the probe showed and states no rule (round 4: `--earned-by buglog-row-claims`, the same kind as C2, so cut rather than reworded) |
| M2 | NIT | melious | 3 | the proposed guard would flag `\$0`, which the probe shows is safe | fixed in ac59bf63 | the guard leaves `\$` alone |
| N1 | NIT | melious | 4 | the proposed guard would also fail on `$10`, `$29`, `$35` and `$50`, which the probe left alone | fixed, no further round | the row names those four amounts and leaves the choice to the guard's plan |

Gate ids 20261113T120537Z-56597 (round 1) and 20261113T120825Z-86135 (rounds 1-4): 7 reviewer
seat runs, 116,386 tokens logged plus 26,725 in the first gate. Codex reported UNVERIFIABLE in
every round that the probe is a transcript, not a reproduced run; the row states only what it saw.
