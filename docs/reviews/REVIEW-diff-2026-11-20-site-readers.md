# DIFF review — fix/038-site-readers — every reader of `site:` agrees

Base `b3d507af` (origin/main when the branch was cut) · depth: Normal, tooling fixes in the starter's scripts ·
verdict: no BUG and no counted RISK open after round 6 · 6 rounds · Codex alone (REVIEW-RULES), plus a
fresh-eyes pass in round 1 · this session was started by the Croftweaver manager and made the branch.
Gate id 20261120T093536Z-48119.

Artifact: each round `git diff origin/main...HEAD -- . ':(exclude)docs/reviews/' ':(exclude)docs/BUGLOG.md'`.
BUGLOG prose got a wording read by the author. Evidence per round: `make check`, `scripts/test_site_readers.sh`,
`tests/check_ship_push.sh` (rc 0, 535 checks), and one run of the new suite on GNU grep 3.8 (Debian) in round 6.

| Round | Reviewers | BUG / RISK | What came back |
|---|---|---|---|
| 1 | fresh-eyes (Claude Sonnet sub-agent, read-only; findings fixed, count not recorded); Codex | 2 / 1 | `ORPHAN_EXEMPT` closer with blanks, an escaped quote; the drift test's mutation depended on text |
| 2 | Codex | 1 / 2 | backtick strings; `)` on the next line; the drift test mutated after extraction |
| 3 | Codex | 2 / 0 | `)` on the next line (second time); Unicode spaces before `site:` |
| 4 | Codex | 4 / 0 | a declaration inside a comment, an unrecognized declaration, the old diagnostic test, `//` comments and U+2028 |
| 5 | Codex | 4 / 0 | all in the `ORPHAN_EXEMPT` reader again (an `\|\|` initializer, a declaration in a block comment, `const` split from its name, a re-parsed quote) |
| 6 | Codex | 0 / 0 | clean, on the diff without the `ORPHAN_EXEMPT` reader |

Codex's token cost: about 84,000 per round; the gate's log shows 496,632 tokens in all, fresh-eyes not recorded.

## Disposition

- Round 3 made the `ORPHAN_EXEMPT` reader a strict rule (a cut, as the skill asks, since the kind had earned three
  rounds). It came back in round 4 and round 5. At round 5 the Croftweaver manager decided to take item 4 out of this PR: the
  reader, its tests and its BUGLOG fix were reverted to `origin/main`; the BUGLOG row stays open with the reason.
  A real fix needs a parser or a different place for the list. A plan for that goes through its own gate.
- Re-sorted: the `site:` readers took the Unicode-space finding (round 3) by listing JavaScript's white-space
  characters, and the U+2028 / U+2029 finding (round 4) by ending a `//` comment at them in `js_state`.
  A NBSP before `site:` is matched again, as before this PR.
- GNU grep: the reader's byte-offset and byte-range claims were unverified in rounds 1 to 5. Round 6's run of
  `scripts/test_site_readers.sh` under GNU grep 3.8 passed, in the C and C.UTF-8 locales.
- Not run here: `tests/check_deploy.sh` (needs `npm ci`; CI runs it).
