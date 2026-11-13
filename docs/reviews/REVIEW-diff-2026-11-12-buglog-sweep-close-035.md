# DIFF review — BUGLOG: six rows found done or stale in the 0.35 bug sweep

Artifact: `git diff origin/main...HEAD -- . ':(exclude)docs/reviews/'`, status cells of six rows in
`docs/BUGLOG.md` and nothing else. Depth: Light (log rows only; REVIEW-RULES Light, Codex medium,
one round plus one because round 1 found a BUG in prose). Gate id 20261112T080308Z-36258.
Checks: `make check` passed at 8b2c6947, and after the round 1 fix `check_buglog_rows.sh` and
`check_clean.sh` passed at d3f69f8b. The claims sweep ran before round 1; the only claims it
listed that the change adds are in the six status cells, each checked below.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | 8b2c6947 | full diff | codex | codex 118 s, 91,156 | 2/0/0 |
| 2 | d3f69f8b | full diff, `--verify` | codex | codex 124 s, 66,580 | 0/0/0 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| A1 | BUG | codex | 1 | The pages.dev NEL row was closed as stale "with no `pages.dev` or `workers.dev` address", but the starter's Worker keeps `preview_urls: true`, and the captured version-link answer carries `nel` and `report-to` | fixed | `wrangler.jsonc` line 11; `skills/new-website/scripts/tests/fixtures/pages-vs-worker-headers/curl-8.7.1-worker-redirect-old-page-2026-11-05.txt`, the workers.dev section. The row stays open, marked "moved" to Workers, citing the fixture |
| A2 | BUG | codex | 1 | "`git grep` of the 14 names finds none" is false: `video` appears under `skills/` | fixed | `git grep -nw video origin/main -- skills/`: 24 hits, all prose, fixtures or code, none a skill pointer; `git grep -w` of the other 13 names: none. The cell now says exactly that |

The GEO row: the figures were read on 2026-11-12 from the HTML render of arXiv 2311.09735v3,
Table 1, Overall column ("No Optimization" 19.3; Quotation Addition 27.2, Statistics Addition
25.2, Fluency Optimization 24.7, Cite Sources 24.6, Technical Terms 22.7, Easy-to-Understand 22.0,
Authoritative 21.3, Unique Words 20.5, Keyword Stuffing 17.7). Codex recomputed the percentages
but could not see the paper (UNVERIFIABLE in round 2); the values above are the host's reading.

UNVERIFIABLE (round 2, Codex): the 2026-10-08 live deploy run behind the PUBLISHING row (its own
trail, `REVIEW-diff-2026-10-08-docs-buglog-deploy-by-command-verified-41a6b58.md`, records it);
whether every Preview link, not just the captured version link, carries the NEL headers. The
second is the open question row 59 now carries.

Result: CLEAN, 2 rounds, 2 findings (2 BUG, 0 RISK, 0 NIT), 157,736 tokens logged.
