# DIFF review: the competing-pages check in `website-new-page` (2026-11-23)

Base `32b815ef` (origin/main). Depth: Normal. Seat: Codex alone (REVIEW-RULES; the change is prose, a prompt and
one test file). Each round read the whole diff against the base; rounds 2 and 3 ran with `--verify` and the prior
findings. The brief (evidence file) holds the test records. The host's fresh-eyes pass ran at round 1 (a subagent
that did not write the change) and is logged. The script's warning that the standard pair was not met applies.
The plan was reviewed beforehand in a private hub (PLAN gate, four rounds).

| Round | Reviewer | BUG / RISK / NIT | What came back |
|---|---|---|---|
| 1 (head `efcbef7f`) | Codex | 3 / 2 / 1 | the review prompt lacked the two exclusions; a failed Search Console lookup could pass unnoticed; two BUGLOG claims the code does not support; one test check too coarse |
| 1 | fresh-eyes | 0 / 3 / 4 | ask-trigger lacked the exclusions; BUGLOG size row overstated the limit; RISK clause missed related queries; step 5 did not name an open check; idea row still open; long lines; no check on the exclusion sentence |
| 2 (head `9e436b3a`) | Codex | 3 / 2 / 2 | "no section means the lookup failed" is wrong when the site has no data; two BUGLOG claims (agy cannot be a content seat; a page with a page document is still visible); the proposed size fix dropped Search Console pages; the rewrite exclusion was not pinned; two long lines |
| 3 (head `f18abbe7`) | Codex | 0 / 1 / 0 | the query-filter operator default (see R3-01) |

Tokens and time: round 1 Codex 63,703 (147 s); round 2 70,402 (189 s); round 3 48,118 (125 s). Fresh-eyes: a
subagent, 112,749 tokens.

## Findings

| Id | Sev | Source | Finding | Status |
|---|---|---|---|---|
| R1-01 | BUG | Codex | the review prompt gave no exclusions, so a rewritten page could be flagged for omitting itself | fixed: both exclusions in the template field and the RISK clause |
| R1-02 | RISK | Codex | a failed `--query` lookup omits its section and returns normally | fixed: step 2 says a missing section means the check is open |
| R1-03 | BUG | Codex | BUGLOG proposed a second evidence file; the script refuses it | fixed: removed |
| R1-04 | BUG | Codex | BUGLOG said the list cannot see pages that other sources do see | fixed: qualified |
| R1-05 | RISK | Codex | "exact words only" rests on an unspecified filter operator | fixed: the claim is gone ("takes one query string") |
| R1-06 | NIT | Codex | one test check covered two clauses | fixed: one check per clause |
| F1-01..07 | RISK/NIT | fresh-eyes | see the table above | fixed in `9e436b3a`; the idea row is closed with the PR number |
| R2-01 | BUG | Codex | no section also means "no data in the window" | fixed: step 2 says so |
| R2-02 | BUG | Codex | a sitemap-excluded page with a page document is still visible | fixed |
| R2-03 | BUG | Codex | agy cannot be a `--content` seat | fixed: the row names no seat |
| R2-04 | RISK | Codex | the size fix could drop Search Console pages | fixed: it keeps them and marks the list cut |
| R2-05 | NIT | Codex | the rewrite exclusion was not pinned by test 26 | fixed: its own check |
| R2-06 | NIT | Codex | two over-long lines | fixed |
| R3-01 | RISK | Codex | Search Console query attribution depends on the filter's default operator | refuted as a risk: Google's reference marks `equals` as the default for an omitted operator ("Your expression must exactly equal the row value"); read on 2026-11-23, and the skill no longer claims exact matching. At worst an extra owner question. No code change. |

## What was run

- `bash skills/independent-review/scripts/test_failed_tier_report.sh`: exit 0, "all checks passed", after the last edit.
  `scripts/check_clean.sh` and `scripts/check_buglog_rows.sh`: OK after the last edit.
- Hand guard (before round 1): deleting the competing-pages question from `content-review.md` made the suite exit 1 with
  a FAIL line for each seat; the file was restored and compared with `cmp`.
- Behaviour tests T1 to T4 (fresh subagents, expectations written first): pass. A real site was used; the raw records
  are private. T1 run 1 wrote no brief (my instruction was unclear); run 2 passed.
- `make check`: see the PR.

## Open

Nothing in CI tests step 2, step 3 or the template field. The skill does not say in words that the brief is written
first with the decision open; a clause in step 3 would close it (T1 run 1).
