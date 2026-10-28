# DIFF review: FAQ rich results retired by Google

No plan: a correction of a stale fact, which goes straight to the DIFF review. Gate:
independent-review DIFF, depth Normal (skill instruction text and evals). Seats: Codex counted
in both rounds. GLM 5.3 on melious failed in round 1 (balance empty); by the maintainer's rule
of 2026-10-27 the round stands on Codex alone, so round 2 ran on Codex alone too.

| Round | Findings | Disposition |
|---|---|---|
| 1 | NIT: the schema-markup table row still said "no Google rich result for most sites". NIT: the sentences naming the June removal cited only the May entry | fixed: the row gives the 2026 date; both sentences also cite the removal entry |
| 2 | none | clean |

Source read for the review (in the evidence file each round): Google Search Central's updates
log, https://developers.google.com/search/updates, fetched 2026-10-28 21:07Z. Its 8 May 2026
entry says the FAQ rich result "will no longer appear in Google Search starting May 7, 2026";
its 15 June 2026 entry removes the documentation. The old FAQ documentation URL now redirects
(301) to that removal entry.

Checks before review: `make check` exit 0 ("all checks passed"); skipped on this Mac only, as
everywhere: the Perl minimum-version check (Perl::MinimumVersion not installed; CI runs it)
and the shell cases that need `/proc`. `scripts/check_clean.sh` OK. Both changed evals parse.
`rg -n -U -i 'government\s+and\s+health' skills/` finds nothing left.

Totals: 2 rounds, 2 findings (2 NIT), both fixed. Tokens (script log): 58,565 (Codex 37,980 +
20,585; melious failed before sending).
