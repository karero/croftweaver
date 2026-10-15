# DIFF review — docs/checklist-step5-not-legal-advice — step 5: keeping the monitor on is a risk, not a verdict
Base `da86dfb` · depth: High (a caution in privacy-page advice) · verdict: CLEAN (3 rounds and a wording pass; 13 findings, no BUG) · authority used: POST AUTHORITY — atom A (the owner said yes in chat to adding the NEL item's caution to step 5); WORKTREE-WRITE and BRANCH-COMMIT — atom A

Seats: Codex (config effort; medium for the wording pass), GLM 5.3 on melious, a fresh-eyes sub-agent on the host's model in rounds 1 to 3.

| Round | Head | New findings (BUG/RISK/NIT) | Seats |
|---|---|---|---|
| 1 | `f477e0f` | 0/1/3 | codex 110 s / 49,742 (none); melious 18 s (none); fresh-eyes 72 s |
| 2 | `129a875` | 0/1/4 | codex 76 s / 34,784 (none); melious 75 s (1 NIT); fresh-eyes 70 s |
| 3 | `553000b` | 0/1/2 | codex 87 s / 38,243 (none); melious 89 s (none); fresh-eyes 89 s |
| wording pass | `9be1f2f` | 0/0/0 | codex 69 s / 51,454 |

All findings were on wording, and all came from the fresh-eyes seat except one GLM NIT:
- Round 1: "a risk" and "the question" named nothing in step 5 (RISK). Fixed: the sentence names the open question, whether the NEL item's consent rule (§ 25 TDDDG) reaches the monitor, as not checked. "Either data setting", not the switch.
- Round 2: the caution covered the data setting but not the privacy-page line, which informs and is not consent (RISK); "that" had no clear referent; "the NEL item's *Why off*" was ambiguous. Fixed.
- Round 3: "that line" could be read as a header line (the checklist uses "line" for command output); "keeping it on is ... not a verdict" was a category slip. Fixed in the closing edit `9be1f2f`, which the wording pass read clean.
- Left as they were: "Off avoids the question" holds per domain (the step's *Check*, right after, covers each domain); "not checked" carries no date (it does not age the way a search does).

The final text: "We have not checked whether the consent rule in the *Why off* at the top of this item (§ 25 TDDDG) reaches the monitor. Log host only and a sentence on your privacy page do not answer that: this is a risk, not a verdict, and this is not legal advice. Off avoids the question." `make check` exit 0 on every head.
