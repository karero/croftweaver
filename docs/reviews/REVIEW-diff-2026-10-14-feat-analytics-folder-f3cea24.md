# DIFF review — branch feat/analytics-folder — the site's analytics/ folder (search-console-insights 1.9.0)

Base `de64ec8` · depth: Normal (shipped runtime code and agent instructions; nothing in the High row) ·
verdict: OPEN · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session created
this worktree and branch); POST AUTHORITY not yet held (no PR; one is opened only on the owner's word).

Plan and scenarios: `docs/reviews/SKILL-PLAN-analytics-folder.md` (sent with the diff).

- **Pair:** Codex + GLM 5.3 on melious (`SECOND_SEAT=melious`, `MELIOUS_API_TIMEOUT=900`);
  fresh-eyes Sonnet in round 1.
- **Data check:** no keys, tokens, real site names or people's names in the artifact (grep before
  round 1; `check_clean.sh` exit 0). Owner's OK for this pair on this repo in this session:
  "A2 and A7 are fine, run the review" (2026-10-14, given for the Codex + GLM 5.3 pair).
- **Claims sweep before round 1:** 32 sentences; 1 narrowed ("a folder that exists is never
  rewritten" holds for the scripts, not for a check run twice in a day), the rest checked.
- **Test records before round 1** (head f3cea24): `make test` 264 tests OK, exit 0; `make check` exit 0
  (on cd9860c; f3cea24 changed one sentence of prose).

## Rounds

| Round | Head | Seats | BUG / RISK / NIT (after dedup) | Notes |
|---|---|---|---|---|
| 1 | f3cea24 | Codex (401 s, 91k tokens), GLM 5.3 on melious (346 s, 37k), fresh-eyes Sonnet (184 s, 135k) | 11 / 6 / 3 | four invariants; 18 of the 20 fixed, 2 refuted with evidence |
| 2 (verification) | e496a75 | Codex (medium), GLM 5.3 on melious | running | delta f3cea24..e496a75 |

## Findings

Sources: C = Codex, G = GLM 5.3, S = fresh-eyes Sonnet. Invariants: **A** nothing a run writes under
`analytics/` shows to git unless the owner chose so; **B** what is kept is what was imported;
**C** the evidence is what the page was built from; **D** a download keeps its own date.

| Id | Sev | Source | Where | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | S, C, G | `check_kept_off` | (A) only `analytics/README.md` was checked; `analytics/*.md` in `.gitignore` let `seo.html` through | fixed | every path a run writes, checked in one `git check-ignore --stdin` call before the first write; test: 3 partial rule sets refused, 3 whole-folder rules accepted, the download's own path checked |
| F2 | BUG | C (S, G as RISK) | `check_kept_off` | (A) `--no-index` calls a tracked file ignored; rewriting it is a committable change | fixed | tracked destinations refused (`git ls-files`); a tracked neighbour (the owner's kept AI-check runs, B12) is not; test |
| F3 | RISK | S | facts-check, positioning-check pointers | (A) the files the assistant writes have no script guard and the pointers lacked the precondition | fixed | all three places say: only when `git check-ignore -q analytics/x` succeeds |
| F4 | RISK | S | facts-check pointer | no `mkdir`; `facts_check.py` opens its output without creating folders | fixed | `mkdir -p` added |
| F5 | BUG | C (S as RISK) | `analytics_snapshot.py` | (C) the Bing rows came from a different history file than the page in two cases | fixed | the snapshot uses `search_report.resolve_settings` itself, and takes `--csv`; test |
| F6 | NIT | S | `check_kept_off` | (A) a git error was read as "no repository here" | fixed | only git's own "(or any of the parent directories)" message, in the C locale and with no `GIT_DIR`, means no repository; test with a `GIT_DIR` that points nowhere |
| F7 | RISK | C (×2), S (NIT) | `folder_date` | (D) the file-name date conventions rest on fixtures | refuted | the owner's real downloads of 2026-10-14 are named `…-Features-2026-10-14.zip` and `…_AIPerformanceOverviewStats_10_14_2026.csv` (14 cannot be a month); recorded in `SKILL-PLAN-ai-reports.md`. An unreadable date falls back to today |
| F8 | BUG | C (S NIT) | snapshot `_gsc` | (C) a second fetch on one day kept the first data while the page showed the second | fixed | newer content kept beside (`google-data-2.json`); test; B9 reworded (draft 3) |
| F9 | NIT | S | `keep` | copytree not atomic | fixed | staged as `.partial`, then renamed |
| F10 | BUG | C | snapshot geo-run | (C) the AI-check page shows each assistant's latest answer from any run; only the newest run's answers were kept | fixed | every run the page draws on (`referenced_runs`, the page's own rule); test |
| F11 | BUG | C | snapshot geo-run | (C) a second run on one day was skipped | fixed | per-file keeping, answers per run id |
| F12 | BUG | C (G NIT) | `do_import` | (B) a failed copy after the save left the import half done | fixed | copy first, then save; a failed save removes the copy; test |
| F13 | BUG | C | `keep` | (B) a changed download under the same name kept the old bytes | fixed | kept beside as `-2`; test asserts the kept bytes are the imported ones |
| F14 | RISK | C | positioning trigger | a page list cannot see changed pages | fixed | `git log --since=<last verdict> --name-only -- src/`; the verdict ends with the full page list |
| F15 | BUG | C, G | plan status | "16 new tests" was 15 | fixed | recounted |
| F16 | BUG | G | snapshot | (C) `geo.html` linked to a `seo.html` never written | fixed | links to `#` when the other page is missing; test |
| F17 | BUG | G | `folder_date` | (D) a browser's " (1)" suffix lost the file's date | fixed | optional ` (n)` before the extension; test with both services |
| F18 | RISK | G | link rewrite | a link of an unknown shape would stay pointing into hidden settings, silently | fixed | the snapshot prints a warning for any `href="../` left in a top-level page; test |
| F19 | RISK | G | facts-check flags | `--out`, `--json`, `--history` and exit 1 unverified | refuted | `facts_check.py` usage (lines 16–21) and argparse (1570–1572); S and C verified the same |
| F20 | NIT | G | snapshot | silent skips | fixed | every missing part is named |

Codex's E-E-A-T question settled by Google's own page: "E-E-A-T itself isn't a specific ranking
factor" (Search Central, "Creating helpful, reliable, people-first content", updated 2026-10-05);
the instructions now quote it rather than claim more.

Breakage check: the nine round-1 tests that existed then, plus the updated ones, were run on
f3cea24's code: every one fails there except the failed-save test, which passes there too (round 1
saved after the git check, so nothing was kept either). The link-warning test (F18) was added
afterwards and was not part of that run. Test records after the fixes: `make test` 274 OK, `make
check` exit 0.
