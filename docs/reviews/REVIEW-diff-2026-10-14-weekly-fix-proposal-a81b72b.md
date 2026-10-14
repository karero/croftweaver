# Review trail: the weekly fix proposal (build)

Artifact: branch `feat/weekly-fix-proposal`, the diff against `main` (`fix_proposal.py`, the
report's proposal section in `search_report.py`, `references/fix-proposal.md`, one SKILL.md row,
four evals, their tests, and the design plan's notes). Gate: Normal, DIFF (runtime code that reads
the owner's live pages and writes local state, so never Light). Reviewers: Codex and GLM 5.3 on
melious (`SECOND_SEAT=melious`).

Severity bar, agreed before round 1 (as for the design plan, #297): claims about Google and
Serper that the design plan §1 quotes or measured are not re-raised; the owner's decisions
(D0 to D11, DD0 to DD8) are settled. Rounds stop after one without a BUG, then one wording pass.

## Test records before round 1 (at a81b72b, 2026-10-14)

- `~/.config/gsc-insights/venv/bin/python -m unittest discover -s skills/search-console-insights/scripts/tests`:
  308 tests, OK, exit 0.
- `make check`: all checks passed, exit 0. One soft warning is new: SKILL.md is 501 lines, over
  the 500-line soft budget.
- Behaviour checks already run (design plan §4): rules broken on purpose in a copy, all caught
  (step 2: 11, step 3: 9 plus the word check); eval iteration 1, with the skill 18 of 18, without
  12 of 18; cold starts in Claude Code and Codex (design §3.3).
