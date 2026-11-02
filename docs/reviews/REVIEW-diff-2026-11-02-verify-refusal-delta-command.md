# DIFF review: the --verify refusal with no --base prints the delta command

No plan: a wording change to a refusal, chosen as a small fix instead of a `--since` flag. The
idea came from a closing note where round 2 was refused twice, first for no `--base` and then
for a full diff. From 2026-10-23 to 2026-11-02, transcripts show about 30 such refusals and 6
sessions hitting both in a row. Gate: independent-review DIFF, depth Normal (a script that ships
in the bundle; Light is only for tests and prose no one runs). Seats: Codex + GLM 5.3 on
melious, fresh-eyes on Sonnet in round 1. Gate id 20261102T155014Z-4259.

| Round | Findings | Disposition |
|---|---|---|
| 1 (Codex, GLM 5.3, fresh-eyes Sonnet), head `7df688d1` | BUG (Codex): the printed `git diff … -- .` covers only the current folder when run from a subfolder. RISK (Codex, fresh-eyes): `diff.noprefix`, colour or an external diff make its diff fail the check again. RISK (fresh-eyes): the merge-link line did not say it takes `--base` too, and named `merge_link.sh` bare. RISK (fresh-eyes): `$0` printed bare is not runnable from elsewhere. NIT (fresh-eyes): the test only grepped the line. NIT (fresh-eyes, GLM): the trailing `...`. RISK ×4 (GLM): `-` as stdin, `base_refuse` printing every argument, `has` matching by regex, `not_ran` existing | fixed: the check moved after the repository root is known, and the command is the mismatch refusal's remedy (`git -C <root> diff --no-ext-diff --no-color --no-textconv -M --src-prefix=a/ --dst-prefix=b/ <head> HEAD …`); fixed: the merge link says "with the same --base" and both scripts are named by full path; fixed: `<your other options>`; fixed: T3r runs the printed command from a subfolder under `diff.noprefix` and checks the base check accepts its diff, with a control showing the plain form is refused there, and T3p checks the full path when run as `bash independent_review.sh`. In a scratch copy, the script at `origin/main` and at `7df688d1` each fail 6 of the new checks. Refuted (GLM): usage line 205 takes `-`; line 566 prints every argument; the test's `has` is `grep -qF` (line 43); `not_ran` is at line 47 |
| 2 (Codex, GLM 5.3), delta `7df688d1..c7b86172` | Codex: none. RISK (GLM): the comment's "whatever … diff config" overclaims, and the flag equality is unsupported. RISK (GLM): the merge link's argument order is unchecked. NIT (GLM): T3p omits `--depth normal` | fixed: the comment now says the flags override the diff config the check refuses; refuted: the flags match the remedy line character for character; refuted: the order matches `merge_link.sh`'s usage (line 27) and SKILL.md step 6; fixed: `--depth normal` added |
| re-gate, not a round (Codex alone), delta from `c7b86172` | pending | pending |

Checks: `bash skills/independent-review/scripts/test_base_check.sh` PASS after each fix.

Totals so far: 2 rounds, 13 findings (1 BUG, 9 RISK, 3 NIT): 8 fixed, 6 refuted (one RISK was
part fixed, part refuted, and is counted in both). Tokens (script log): 135,499 for rounds 1
and 2; fresh-eyes 101,633.
