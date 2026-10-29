# DIFF review: independent-review, the claims sweep at every depth

No plan: a wording change to a skill's instructions, which goes straight to the DIFF review.
Gate: independent-review DIFF, depth Normal (skill instruction text). Seats: Codex + GLM 5.3 on
melious, plus a fresh-eyes pass (Sonnet) in round 1.

Why: on #442, a Light review of a one-row prose change, Codex corrected two claims in rounds 1
and 2. The claims sweep, run afterwards on that commit, lists both sentences; step 2, where the
sweep lives, is headed "Normal and High", so nothing asked a Light review to run it. The sweep
output and #442's review comment went to the seats as the evidence file each round.

| Round | Findings | Disposition |
|---|---|---|
| 1 (Codex; melious out of balance, no rerun owed; fresh-eyes Sonnet) | Codex: none. Fresh-eyes: F1 RISK, the rule sat only in the sweep paragraph under a heading that sends Light readers past step 2. F2 NIT, "every depth" read as unconditional. F3 NIT, `references/claims-sweep.md`'s heading is silent on depth | F1 fixed: step 2's heading now says Light still runs the sweep on a prose change (the heading rather than the Light row, which the maintainer's working rules replace for his sessions). F2 fixed: "A prose change gets the sweep at every depth". F3 refuted: SKILL.md is the entry point and sends readers to the reference from step 2 |
| 2 (Codex alone; melious out of balance) | none; F1 and F2 verified, F3's refutation accepted | clean |

Checks before each round: `make check` exit 0 ("all checks passed"). The claims sweep on the
change lists the new sentence itself; it states a rule, not a fact about a tool.

Totals: 2 rounds, 3 findings (1 RISK, 2 NIT): 2 fixed, 1 refuted. Codex alone both rounds: the
GLM 5.3 seat on melious failed with an empty balance, and by the maintainer's rule of
2026-10-27 each round stands on Codex. Tokens (script log): 174,727 (Codex 39,085 + 28,419,
fresh-eyes 107,223).
