# DIFF review — report folders (#406)

Branch `feat/report-folders`. Depth: **Normal** (skill text that agents load). Seats: codex
(gpt-6.1-sol, read-only) and melious (glm-5.3), and a fresh-eyes pass (Claude Sonnet, Agent tool)
in round 1. The owner consented in chat, this session (2026-10-25), to "send the PR A and PR B
diffs (public Croftweaver code, no secrets) to Codex and to GLM 5.3 on melious.ai, plus a Sonnet
fresh-eyes pass in round 1": "Yes, for both PRs (Recommended)".

## Round 1 — `5d2df9f0`, base `11a13e2d`
`reviewers: codex OK, melious OK` · `timings: codex 293s (99571 tokens), melious 108s (15499 tokens)`
· fresh-eyes 97 s, 109,856 tokens · gate `20261025T064326Z-57864`

| id | sev | seat | status | why |
|---|---|---|---|---|
| C2 | BUG | codex | fixed | Phase 2's `independent_review.sh WORDING-GUIDE.md` misses a guide kept in `docs/`; now `<path to WORDING-GUIDE.md>` |
| C1 | RISK | codex | fixed | A copy in the root or `docs/` beside one already in `docs/seo/`: now "if more than one of the root, `docs/` and `docs/seo/` has a copy, move nothing and ask" |
| E1 | RISK | fresh-eyes | fixed | `git mv`/`mv` into a missing `docs/seo/` fails (reproduced by the seat); `mkdir -p docs/seo` first |
| E2 | RISK | fresh-eyes | fixed | `docs/launch/` named before any skill writes it; now "beside the site's other report folders in `docs/`" |
| E3 | RISK | fresh-eyes | fixed | `seo-findings-template.md` carries a per-query Search Console table into git; the findings now carry only the rows their verdicts rest on, and in a public repo the assistant asks first |
| G1 | RISK | melious | fixed | SKILL.md and geo-check.md named different homes for the answers; geo-check.md and the BUGLOG row now say both (`~/.config/gsc-insights/geo/` and the snapshot's `analytics/` copy) |
| G2 | RISK | melious | refuted | The plist location: `schedule_tracking.sh:33–34` sets `LA_DIR=$HOME/Library/LaunchAgents` and `LOG_DIR=$HOME/.config/gsc-insights/logs`; codex and fresh-eyes verified it too |
| G3 | RISK | melious | refuted | `--out` creates no folder and overwrites: `gsc_query.py:629–630`, `bing_query.py:353–354` call `Path(args.out).write_text(report)`; codex checked `write_text`'s mode `w` (no `mkdir`) |
| G4 | RISK | melious | refuted, and E7 fixed | The run folder's name: `analytics_snapshot.py` writes `<run date>_geo-run/` (its lines 11–14, verified by fresh-eyes); the bullet now says "where the snapshot has copied the run" |
| G5 | RISK | melious | fixed | The `--keep-in` and snapshot destinations: the sentence now gives their flags, `--keep-in <site folder>` and `--site-dir <site folder>` (`analytics-folder.md`) |
| E4 | NIT | fresh-eyes | fixed | Where the raw SERP snapshots go: beside the findings in `docs/seo/` |
| E5 | NIT | fresh-eyes | fixed | `seo-audit/SKILL.md` went over the 500-line soft budget; the paragraph is one line, 500 lines |
| E6 | NIT | fresh-eyes | fixed | The scripts' usage text still showed `--out report.md` / `bing.md` |
| E7 | NIT | fresh-eyes | fixed | The conclusions file names a folder that exists only after a snapshot; and "say what the file holds" before asking |
| G6 | NIT | melious | fixed | The BUGLOG row overstated: it now says the documented `--out` paths changed |
| G7 | NIT | melious | fixed | "Built for a low-volume site" ran on after the new sentence; now its own paragraph |

Substantive BUG: C2. Round 2 owed. `make check` exit 0 after the fixes (`b339e32f`); `origin/main`
merged in (`9d8b42f6`), touching none of this PR's files.

## Round 2 — verification of `b339e32f` against `5d2df9f0`
`reviewers: codex OK, melious OK` · `timings: codex 128s (57016 tokens), melious 149s (19444 tokens)`
· gate so far 301,386 tokens logged plus fresh-eyes 109,856. Both seats confirmed every round-1
row; codex also confirmed the three refutations (G2, G3, G4). No BUG.

| id | sev | seat | status | why |
|---|---|---|---|---|
| C8 | RISK | codex | fixed | The scripts' usage text left the `--out` path unquoted; a site folder with a space splits it (reproduced in zsh). Now quoted, as in SKILL.md |
| G8 | RISK | melious | fixed | `seo-findings-template.md`'s query table still invited the full export; it now says only the queries the verdicts rest on, the full export stays in `analytics/` |
| G9 | NIT | melious | refuted | "The scripts' usage text did not change": it did (`b339e32f`, `gsc_query.py:32`, `bing_query.py:20–21`); round 2's artifact left those two files out by mistake, and codex, which reads the files, verified the change |
| G10 | NIT | melious | fixed | The BUGLOG row named `~/.config/gsc-insights/` where geo-check.md names `~/.config/gsc-insights/geo/` |
| G11 | NIT | melious | fixed | The kept-report paragraph read as part of the format list; it now starts **Keeping the report:** (no extra line: the file stays at 500) |

Round 3 checks round 2's fixes, with the scripts and the template in its artifact.

## Round 3 — verification of `c19ea9d5` against `b339e32f`
`reviewers: codex OK, melious OK` · `timings: codex 60s (33072 tokens), melious 12s (4639 tokens)` ·
both: "No BUG/RISK/NIT findings." Round 2's fixes confirmed.

## Closing re-gate (not a round)
Round 2's artifact left out the two scripts (their round-1 usage-text hunk), so neither seat's
chain covers that segment. One codex pass over the whole change, `origin/main...HEAD` without
`docs/reviews/`, re-gates the head the stamp names.
`reviewers: codex OK` · `timings: codex 316s (93058 tokens)` · base `8ec4cb88`, head `11c9da00`.

| id | sev | seat | status | why |
|---|---|---|---|---|
| C9 | RISK | codex | fixed | Moving `SEO-FINDINGS.md` or `SEO-CHANGELOG.md` into `docs/seo/` breaks their relative links and the links to them; the move rule now says to fix both (`3a638bc5`) |

## Round 4 — verification of `3a638bc5` against `11c9da00`, earned by C9
`--earned-by moved-links` · `reviewers: codex OK, melious OK` · `timings: codex 48s (14117
tokens), melious 22s (3345 tokens)` · both: "No BUG/RISK/NIT findings."

## Verdict: CLEAN
4 rounds and a closing re-gate; findings 1 BUG, 12 RISK, 9 NIT (round 1: 1/9/6; round 2: 0/2/3;
round 3: none; re-gate: 0/1/0; round 4: none). Refuted: G2, G3, G4, G9, each with its evidence
above. The stamp's chain is codex's: the full pair `8ec4cb88...11c9da00` (the re-gate), then the
delta to `3a638bc5` (round 4); later commits touch `docs/reviews/` only. Reviewer tokens by the
timings lines, rounds 1–4 and the re-gate: 339,761 (codex 296,834, melious 42,927), plus
fresh-eyes 109,856; the wording pass and its confirmation below add codex 73,770. `make check` exit 0 at `b339e32f`; the later
changes are prose in skill files.

## Wording pass (not a round)
One codex pass over the trail, scoped to factual contradictions · `timings: codex 142s (51875
tokens)`. One finding: the verdict line said 13 RISK where the tables add up to 12; fixed.
Confirmation of that fix · `timings: codex 48s (21895 tokens)`: it found the token total no longer
matched the timings once the wording pass's line was added; the total is now labelled by what it
covers, and the wording pass and confirmation are counted beside it.
