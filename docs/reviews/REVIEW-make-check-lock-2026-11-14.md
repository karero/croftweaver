# Review trail: the `make check` lock, 2026-11-14

What was reviewed: `scripts/check_lock.sh`, its test `scripts/test_check_lock.sh`, the `Makefile` split
(`check` takes the lock, `check-run` holds the guards), the guard lists, the `clean.yml` Linux job and
the docs rows. Built from the plan of the same name in the private plans repository.

Gate: the `independent-review` DIFF gate at Normal depth (a second model family was needed, since the
change is code that other runs depend on). Two seats on every round, Codex and GLM 5.3 on melious.ai, plus
a fresh-eyes read in round 1. Five rounds; the last found nothing.

| Round | Commit reviewed | Findings | What came out of it |
|---|---|---|---|
| 1 | a6ab37a6 | 11 (F1-F11) | TERM or HUP to the lock holder alone freed the lock while the guards ran on: the holder now forks the command, passes both signals on and keeps the lock until the command ends (case T8). Wrong CDPATH exclusion reason and an overclaiming test header fixed. Rest: wording, one waived, two accepted by design. |
| 2 | bcb81dea | 7 (G1-G7) | Handlers moved before the fork; lock file forced to mode 0600 (the open mode only applies on creation); a Perl warning printed on every run, now silenced and guarded by case T9. One refuted (POSIX is loaded). |
| 3 | 3ae34d7f | 5 (H1-H5) | The child could consume a forwarded signal before resetting handlers: TERM and HUP are now blocked across the fork. T8 now covers HUP, the README claim had no test. `chmod` failure now stops the run. Descriptor marked close-on-exec explicitly. |
| 4 | 89c52c8d | 6 (I1-I6) | Both seats: the handlers were installed a moment before the signals were blocked, so a handler could run with no command pid. Fixed by a cut: the mask comes first. Test header names T9 as a direct case; the close-on-exec call is checked. One waived (a signal after the command ended could meet a reused pid). |
| 5 | 8db7d5fb | 0 | Both seats clean. |

29 findings in all, counting waived and refused ones. Tokens as the gate printed them: Codex 213,614
(56,812 + 60,241 + 36,636 + 30,095 + 29,830), GLM 147,055 (45,660 + 35,349 + 23,001 + 26,485 + 16,560), the
round-1 fresh-eyes read 152,530; 513,199 in all.

## Left as it is, on purpose

- A signal landing in the microseconds between the fork and the mask restore, or in the gap before the
  mask, cannot be hit on demand, so no test covers it. The order of the code is the guard.
- The no-Perl case (T5 in the plan) is not tested: it would need a PATH without Perl.
- A bare `make check-run` runs the guards without the lock. It is labelled internal and not covered.
- A holder pid that was reused can mislabel the holder in a refusal. The refusal itself is right.
- The explicit close-on-exec call is not mutation-tested: Perl already marks descriptors above 2, and the one
  probe that could tell them apart (a closed standard input) was inconclusive. What is measured: a command
  that leaves a background process behind does not keep the lock.
- Linux: the lock test was run on macOS only. The pull request's own run of the `check-lock` job is the
  first Linux run, and merging waits for it.

## Checks the author ran

- The lock test after every round (12 cases, all passing at the last commit), and mutations: with the HUP
  handler deleted T8 fails for HUP only; with the TERM handler deleted T8 fails; with the no-warnings pragma
  removed both T9 cases fail; with the lock removed from `check`, T1 fails.
- The four cheap guards (`check_package_scripts.sh`, `check_cdpath_safe.sh`, `check_clean.sh`,
  `test_mktemp_guard.sh`) on the last commit.
- A full `make check` on the final tree: see the pull request description for its result.
