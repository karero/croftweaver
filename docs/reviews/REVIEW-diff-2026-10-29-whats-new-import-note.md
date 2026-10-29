# DIFF review: whats-new prints how to check a template test's site imports

No plan: a wording change to the report, chosen as a small note instead of a build (the idea
came from the genai-wednesday.de 0.34 update, where a new test imported a site file the site
lacked). Gate: independent-review DIFF, depth Normal (a script every site owner runs). Seats:
Codex + GLM 5.3 on melious, fresh-eyes on Sonnet in round 1.

| Round | Findings | Disposition |
|---|---|---|
| 1 (Codex; melious out of balance, no rerun owed; fresh-eyes Sonnet) | BUG (Codex): the printed command left the suite path unquoted, so a path with a space split in two. RISK (Codex): it scanned only top-level specs and single-quoted imports. NIT (fresh-eyes): no test asserts the note. NIT (fresh-eyes): a spec deleted upstream still triggers the note | fixed: the path is quoted and the command runs `grep -r` with `--include='*.spec.ts'` and a pattern that takes either quote; fixed: `test_whats_new.sh` checks the exact printed line and runs it against a fixture spec that imports a site file (both checks fail on the round-1 command and with the note removed); refuted: the note makes no claim about the spec that triggered it |
| 2 (Codex alone; melious out of balance) | none; F1 to F4 confirmed | clean |

Checks: before round 1, `make check` exit 0. Before round 2, `bash scripts/test_whats_new.sh`
("all whats-new missing-file tests passed") and `scripts/check_clean.sh` OK; the printed
command run in zsh lists the 12 template-spec imports, also from a folder whose path has a
space. `make check` ran again on the final tree, with this trail and the BUGLOG row.

Totals: 2 rounds, 4 findings (1 BUG, 1 RISK, 2 NIT): 3 fixed, 1 refuted. Codex alone counted
each round: the GLM 5.3 seat failed with an empty balance, and by the maintainer's rule of
2026-10-27 each round stands on Codex. Tokens (script log): 153,365 (fresh-eyes 96,026; Codex
29,666 + 27,673).
