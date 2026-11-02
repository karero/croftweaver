# DIFF review: the --verify refusal with no --base prints the delta command

No plan: a wording change to a refusal, chosen as a small fix instead of a `--since` flag. The
idea came from a closing note where round 2 was refused twice, first for no `--base` and then
for a full diff. From 2026-10-23 to 2026-11-02, transcripts show about 30 such refusals and 6
sessions hitting both in a row. Gate: independent-review DIFF, depth Normal: a script that ships
in the bundle, and the maintainer's rule of 2026-10-09, which replaces SKILL.md's Light row, keeps
tooling fixes out of Light. Seats: Codex + GLM 5.3 on
melious, fresh-eyes on Sonnet in round 1. Gate id 20261102T155014Z-4259.

| Round | Findings | Disposition |
|---|---|---|
| 1 (Codex, GLM 5.3, fresh-eyes Sonnet), head `7df688d1` | BUG (Codex): the printed `git diff … -- .` covers only the current folder when run from a subfolder. RISK (Codex, fresh-eyes): `diff.noprefix`, colour or an external diff make its diff fail the check again. RISK (fresh-eyes): the merge-link line did not say it takes `--base` too, and named `merge_link.sh` bare. RISK (fresh-eyes): `$0` printed bare is not runnable from elsewhere. NIT (fresh-eyes): the test only grepped the line. NIT (fresh-eyes, GLM): the trailing `...`. RISK ×4 (GLM): `-` as stdin, `base_refuse` printing every argument, `has` matching by regex, `not_ran` existing | fixed: the check moved after the repository root is known, and the command is the mismatch refusal's remedy (`git -C <root> diff --no-ext-diff --no-color --no-textconv -M --src-prefix=a/ --dst-prefix=b/ <head> HEAD …`); fixed: the merge link says "with the same --base" and both scripts are named by full path; fixed: `<your other options>`; fixed: T3r runs the printed command from a subfolder under `diff.noprefix` and checks the base check accepts its diff, with a control showing the plain form is refused there, and T3p checks the full path when run as `bash independent_review.sh`. In a scratch copy, the script at `origin/main` and at `7df688d1` each fail 6 of the new checks. Refuted (GLM): usage line 205 takes `-`; line 566 prints every argument; the test's `has` is `grep -qF` (line 43); `not_ran` is at line 47 |
| 2 (Codex, GLM 5.3), delta `7df688d1..c7b86172` | Codex: none. RISK (GLM): the comment's "whatever … diff config" overclaims, and the flag equality is unsupported. RISK (GLM): the merge link's argument order is unchecked. NIT (GLM): T3p omits `--depth normal` | fixed: the comment narrowed; refuted: the flags match the remedy line character for character; refuted: the order matches `merge_link.sh`'s usage (line 27) and SKILL.md step 6; fixed: `--depth normal` added |
| re-gate, not a round (Codex alone), delta `c7b86172..9d8485cd` | BUG (prose): this trail said Light is only for tests and prose, against SKILL.md's Light row. RISK: the comment still claimed the flags override all diff config the check refuses (`diff.submodule`, for one, is not covered) | fixed: the depth line names the maintainer's rule that replaces SKILL.md's Light row; fixed: the comment names the four kinds of config the flags override (prefix, colour, external diff, textconv) |
| confirmation (Codex alone, `--wording-pass`), delta `9d8485cd..1187a7b0` | G1 and G2 verified fixed. RISK (follow-up, not a finding on the fix): the maintainer's rule is not quoted | refuted: the rule is in the maintainer's own review rules, outside this repo (its Light paragraph, dated 2026-10-09: "tooling fixes and plans never are" Light) |
| CI fix, Light (Codex alone, medium), delta `5fce92c7..b43e3508`, gate 20261102T192248Z-75488 | The macOS stock-tools job failed T3p inside the unzipped handoff zip: the scripts folder is in no git repository there, so the script refused as "not inside a git work tree" before the --verify refusal. Reproduced from a copy outside any repository with /bin/bash 3.2 and bash 5.3. Codex: no findings | T3p now runs a copy of the scripts folder inside a throwaway repository with one commit. Passes outside a repository (bash 3.2, stock tools) and in the checkout (bash 3.2 and 5); the script at `origin/main` still fails the 6 new checks, and printing a bare `$0` fails T3p. Light: the delta is the project's own test only |

Checks: `bash skills/independent-review/scripts/test_base_check.sh` PASS after each fix.
`make check` exit 0 on `c7b86172` ("all checks passed"; one local SKIP, the Perl
minimum-version check, as Perl::MinimumVersion is not installed here; CI runs it). On the final
tree, `test_base_check.sh`, `check_clean.sh` and `check_pipefail_pipes.sh` pass again.
After the CI fix (`b43e3508`), with macOS's /bin/bash 3.2 and BSD awk, sed, tr and grep first on
PATH as CI's stock-tools job puts them: `make smoke` exit 0, then `make check` inside the unzipped
handoff zip exit 0 (its usual skips: no git clone, no workflow file, no Perl::MinimumVersion).

Totals: 2 rounds, a re-gate, a confirmation and a Light round for the CI fix, 16 findings (2 BUG, 11 RISK, 3 NIT): 10
fixed, 7 refuted (one RISK was part fixed, part refuted, and is counted in both). Tokens
(script log): 247,597 (rounds 1 and 2: 135,499; re-gate 62,836; confirmation 49,262), plus
fresh-eyes 101,633; the CI fix's Light round 31,737.
