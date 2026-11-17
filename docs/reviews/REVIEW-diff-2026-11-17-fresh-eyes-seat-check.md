# Review trail: the fresh-eyes seat check (DIFF)

DIFF gate, Normal, 2026-11-17; gate `20261117T150439Z-17449`, on `2694abb0` against the merge
base `5a0b3010`. Codex alone (REVIEW-RULES: the change touches no High-row topic). The fresh-eyes
seat (Sonnet, medium) was started before the script this time and logged with `--gate-id`, from
the command the new round-1 note printed. Raw output stays in the session's scratchpad.

| Round | Seats | Found | What changed |
|---|---|---|---|
| 1 | Codex (50,916 tokens); fresh-eyes, Sonnet medium (117,063 tokens) | Codex: none. Fresh-eyes: 2 NIT | Nothing. NIT 1: run as root, `[ -w ]` is always true, so the two read-only cases would fail loudly (CI runs as a normal user). NIT 2: a line logged without `--round` is not counted; the refusal already names `--round <r>` |

1 round; 2 findings (2 NIT); no BUG or RISK. The gate's log: 167,979 tokens over 2 seat runs.

Before the gate: `test_round_checks.sh` 117 of 117, `test_base_check.sh` passed, the repo's
quick checks passed, and the plan's three mutations were each caught (reverting the refusal:
7 checks fail; the note printing always: 1; dropping the gate filter: 8).
`test_failed_tier_report.sh` failed different checks on each run, on main as on the branch
(16 on main, 3 on the branch; none passes `--round`), with the Mac at a load average near 840;
its one real failure, the gates case refused at round 2, was fixed by logging a fresh-eyes line
after each round 1. CI is the clean run.
