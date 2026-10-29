# DIFF review: content guide, Google's E-E-A-T wording and a claims rule

No plan: wording corrections to a skill's instructions, which go straight to the DIFF review.
Gate: independent-review DIFF, depth Normal (skill instruction text). Seats: Codex + GLM 5.3 on
melious.

Source fetched on 2026-10-29 and quoted verbatim in the evidence file each round: Google's
"Creating helpful, reliable, people-first content" (last updated 2026-10-05).

| Round | Findings | Disposition |
|---|---|---|
| 1 (Codex alone; melious out of balance, no rerun owed) | BUG: the starter's `templates/content-guide.md` still said search and AI engines reward E-E-A-T and lacked the claims rule, so new sites' `CONTENT_GUIDE.md` would contradict the skill. Unsupported: "a figure that loses its source gets repeated without it" | fixed: the template's EEAT section and new-page checklist now match the skill; the sentence is cut |
| 2 (Codex alone; melious out of balance) | none | clean |

Checks before each round: `make check` exit 0 ("all checks passed"). `scripts/check_clean.sh` OK;
`scripts/check_buglog_rows.sh` OK.

Totals: 2 rounds, 2 findings (1 BUG, 1 unsupported sentence), both fixed. Codex alone both
rounds: the GLM 5.3 seat on melious failed with an empty balance, and by the maintainer's rule
of 2026-10-27 each round stands on Codex. Tokens (script log): 92,564 (Codex 48,486 + 44,078).
