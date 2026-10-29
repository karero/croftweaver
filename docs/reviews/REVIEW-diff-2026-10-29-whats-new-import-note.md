# DIFF review: whats-new prints how to check a template test's site imports

No plan: a wording change to the report, chosen as a small note instead of a build (the idea
came from the genai-wednesday.de 0.34 update, where a new test imported a site file the site
lacked). Gate: independent-review DIFF, depth Normal (a script every site owner runs). Seats:
Codex + GLM 5.3 on melious, fresh-eyes on Sonnet in round 1.

| Round | Findings | Disposition |
|---|---|---|
| 1 (Codex; melious out of balance, no rerun owed; fresh-eyes Sonnet) | BUG (Codex): the printed command left the suite path unquoted, so a path with a space split in two. RISK (Codex): it scanned only top-level specs and single-quoted imports. NIT (fresh-eyes): no test asserts the note. NIT (fresh-eyes): a spec deleted upstream still triggers the note | fixed: the path is quoted and the command runs `grep -r` with `--include='*.spec.ts'` and a pattern that takes either quote; fixed: `test_whats_new.sh` checks the exact printed line, which pins the quoted path, `-r` and the pattern as text, and runs it against a fixture spec with one top-level, single-quoted site import; no fixture has a spaced path, a subfolder spec or a double-quoted import, so those three are pinned by the exact line only. In a scratch copy both checks failed on the round-1 command and with the note removed; refuted: the note makes no claim about the spec that triggered it |
| 2 (Codex alone; melious out of balance) | none; F1 to F4 confirmed | clean |
| wording pass (Codex alone; melious out of balance) | RISK: the trail's "both checks fail on the round-1 command" read as if the tests pinned the spaced-path, subfolder and quote fixes | fixed: the round-1 row now says what each check pins and what no fixture covers |

Checks: before round 1, `make check` exit 0. Before round 2, `bash scripts/test_whats_new.sh`
("all whats-new missing-file tests passed") and `scripts/check_clean.sh` OK; the printed
command run in zsh lists the 12 template-spec imports, also from a folder whose path has a
space. `make check` exit 0 again on the tree with this trail and the BUGLOG row ("all checks
passed"; one local SKIP, the Perl minimum-version check, as Perl::MinimumVersion is not
installed here; CI runs it).

Totals: 2 rounds and a wording pass, 5 findings (1 BUG, 2 RISK, 2 NIT): 4 fixed, 1 refuted.
Codex alone counted each time: the GLM 5.3 seat failed with an empty balance, and by the
maintainer's rule of 2026-10-27 each round stands on Codex. Tokens (script log): 191,269
(fresh-eyes 96,026; Codex 29,666 + 27,673 + 37,904).
