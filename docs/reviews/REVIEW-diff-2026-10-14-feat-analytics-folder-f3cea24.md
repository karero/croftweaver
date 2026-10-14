# DIFF review — branch feat/analytics-folder — the site's analytics/ folder (search-console-insights 1.9.0)

Base `de64ec8` · depth: Normal (shipped runtime code and agent instructions; nothing in the High row) ·
verdict: CLEAN (5 rounds; closing re-gate clean on 94c6c4a) · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session created
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
| 2 (verification) | e496a75 | Codex medium (291 s, 63k tokens), GLM 5.3 on melious (417 s, 41k) | 3 / 5 / 5 (F21–F31) | delta f3cea24..e496a75; three round-1 fixes partial (F1 → F21, F6 → F22, F10 → F23): round 3 owed |
| 3 (verification) | 6ebb7cf | Codex medium (328 s, 68k tokens), GLM 5.3 on melious (424 s, 33k) | 2 / 4 / 4 (F32–F41) | delta e496a75..6ebb7cf; F32 and F33 substantive: round 4 earned (kinds ai-evidence, gsc-evidence); F32 is the third link of F10 → F23, so the fix is a cut, not a patch |
| 4 (verification) | 7cb141a | Codex medium (391 s, 84k tokens), GLM 5.3 on melious (515 s, 44k) | 2 / 3 / 2 (F42–F48) | delta 6ebb7cf..7cb141a; earned by ai-evidence, gsc-evidence. F42 and F43 substantive: round 5 earned by the same two kinds, so it needs a cut (below) |
| 5 (verification) | f74764a | Codex medium (280 s, 64k tokens), GLM 5.3 on melious (158 s, 21k) | 0 / 1 / 3 (F49–F52; Codex's two BUG labels triaged below) | delta 7cb141a..f74764a, with the cut. No substantive BUG: **the rounds end** (stop condition a2). Its fixes are locally_verified, not externally re-verified until the closing re-gate |
| re-gate (not a round) | 94c6c4a | Codex medium only (148 s, 50k tokens) | 0 / 0 / 0 | delta f74764a..94c6c4a: F50 and F51's code at full scope, the trail and plan row for facts only. Clean |

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

| F21 | BUG | C (G NIT) | `plan`/`keep` | caused-by: F1 (partial). (A) the `.partial` staging name was written but never checked; a failed copy could leave it | fixed | `plan()` lists each staging path with its final path; a failed copy removes its staging file; tests: rules that ignore the final names but not `.partial` (snapshot and import), and a copy that fails half-way |
| F22 | BUG | C | `check_kept_off` | caused-by: F6 (partial). (A) a failing `git ls-files` (unreadable index) read as "nothing tracked" | fixed | every git answer's exit code is read: `ls-files` must succeed, `check-ignore` must answer 0 or 1; test with a broken `GIT_INDEX_FILE` |
| F23 | BUG | C | `referenced_runs` | caused-by: F10 (partial). (C) the run set came from today's history, not the kept page's: a run after the page (its page never written) shifted it | fixed | only rows up to the page's own run (the page's view when it was built: `build_report` takes the latest per (engine, mode, slot)); test with an older displayed run and a later unpublished one |
| F24 | RISK | C, G | three pointers | (A) the precondition for files the assistant writes tested a sample path, and not tracked status | fixed | per file: `git check-ignore -q --no-index` succeeds and `git ls-files` prints nothing |
| F25 | RISK | C (G NIT) | positioning trigger | committed changes only; `src/` assumed | fixed | `git log` plus `git status --porcelain` on the pages folder (`src/` here; other sites, ask); no git: judge every page |
| F26 | RISK | C (G NIT) | leftover-link warning | double-quoted lowercase only; the kept run page unchecked | fixed | any quoting or case; the run page checked too (only `../seo.html` allowed there); test |
| F27 | RISK | G | `check_kept_off` | `rev-parse` can say `false` with exit 0 | fixed | anything but `true` refuses; test with the `.git` folder as the site folder |
| F28 | RISK | G | `referenced_runs` | the page's selection rule and the site spelling were assumed | refuted | read `geo_check.build_report` (lines 1232–1239): rows filtered by `r.get("site") == site` with `site = normalize_site(domain)`, latest per `(engine, mode, slot)`; the snapshot does the same (its mode filter only drops keys, so the kept set is a superset) |
| F29 | NIT | C, G | snapshot | a missing answers folder was skipped silently | fixed | named in the output; test |
| F30 | — | C | F7, E-E-A-T (UNVERIFIABLE) | the same questions as round 1 | stands as recorded | evidence in F7's row and below |
| F31 | — | G | `check_kept_off` callers (UNVERIFIABLE) | a string caller would be iterated by character | refuted by reading | the only callers, `do_import` and `snapshot`, pass lists |

| F32 | BUG | C (round 3) | `referenced_runs` | caused-by: F23 (partial). (C) the cut-off still guessed: a page built for an older run can show a later run's answer | fixed by a cut | the inference is no longer the source: `geo_check.build_report` writes `<meta name="geo-runs">` with the runs whose answers it shows, and the snapshot keeps those; a page from before falls back to the inference and says so. Test through a real (stubbed) check run, `build_report` and `analytics_snapshot.main` |
| F33 | BUG | C | snapshot `_gsc` | (C) `search_report` renders fresh data when `google-data.json` cannot be saved, so an older file sat beside a newer page | fixed | the page carries `<meta name="gsc-data-sha256">`, the SHA-256 of exactly the text written to `google-data.json` (one serialiser, `data_text`); the snapshot keeps the file only when it matches, else says so. Tests through `search_report.build`: match kept, a different file not kept |
| F34 | RISK | C | three pointers | (A) an `ls-files` failure also prints nothing | fixed | "succeeds and prints nothing" |
| F35 | RISK | C (G NIT, fragments) | link warning | (C) an unquoted `HREF=../..` passed both patterns; `../seo.html#x` warned wrongly | fixed | links read with `html.parser` as a browser does, fragments and queries ignored for the allowed link; test |
| F36 | RISK | G | `keep`'s cleanup | `unkeep` not visible in the delta | refuted by reading | `unkeep` is defined in `_analytics.py` (after `keep`), handles files and folders, and the half-copy test exercises it |
| F37 | RISK | G | `plan`/`keep` | the staging name is shared only by comment | fixed | one constant, `PARTIAL`, used by both |
| F38 | NIT | G | `referenced_runs` | run ids compared as strings | fixed | compared by their UTC time prefix; test with a same-second pair that sorts the wrong way as strings |
| F39 | NIT | G | run-page warning | named the file before `keep()` could number it | fixed | warns with the path `keep()` returned |
| F40 | NIT | G | test | a read without `encoding` | fixed | `encoding="utf-8"` |
| F41 | — | C | F7, E-E-A-T (UNVERIFIABLE) | as before | stands as recorded | — |

| F42 | BUG | C (round 4) | snapshot | caused-by: F32 (partial). (C) a page from before run lists still went through the inference, which can keep the wrong runs | fixed by a cut | the inference is gone (`referenced_runs` deleted): such a page is kept, its answers are not, and the output says to rebuild it with `geo_check.py --report`; test |
| F43 | BUG | C (G RISK) | `search_report.write_atomic` | (C) text-mode writing turns `\n` into CRLF on native Windows, so the saved data never matched its fingerprint there | fixed | `write_atomic` writes `text.encode("utf-8")` as bytes; test asserts the file's SHA-256 equals the page's and holds no CRLF. **Limit:** this Mac writes LF either way, so the test passes on the old code too; the fix is right by construction, not shown failing here |
| F44 | RISK | C | snapshot `_gsc` | (C) the bytes checked were not the bytes kept: `keep()` re-read the live file | fixed | the checked bytes are staged and kept; test rewrites the live file between check and keep |
| F45 | BUG→NIT | G | snapshot `_gsc` | an unreadable `google-data.json` or `google.html` stopped the whole snapshot (`main` reports it; no traceback, so a NIT under the bar) | fixed | read inside the guarded block, named and skipped; test with a file the user cannot read |
| F46 | NIT | G | tests | three reads without `encoding` | fixed | `encoding="utf-8"` |
| F47 | NIT | G | snapshot | blank lines before `GEO_LINK` | fixed | two blank lines |
| F48 | — | host | `test_analytics.py` | run alone, it could not import the fake Google of `test_search_report` (discovery hid it) | fixed | the tests folder on `sys.path`; the file passes alone and in the suite |

| F49 | BUG (record) | C (round 5) | F45's row | "fixed" overstated it: an earlier read of `google.html` was still unguarded | fixed (record and code) | F45 was partial; see F51 |
| F50 | RISK (Codex: BUG) | C | snapshot | (C) `google.html` read twice: a refresh between the reads could pair page A's copy with page B's fingerprint | fixed | the page is read once and that text serves both; test counts one read. **Rated RISK, not BUG (the author's judgment, told to the owner):** it is F44's kind, which Codex itself rated RISK in round 4 — it needs a refresh to land between two reads in one run |
| F51 | NIT | C, G | snapshot | an unreadable `google.html` stopped the snapshot, and was named as the data file | fixed | named as the page; its data is not kept unchecked; the rest is written; test with a page the user cannot read |
| F52 | NIT | G | tests | an unused import and alias; `hashlib` imported mid-test | fixed | — |

Fix chains: F1 → F21, F6 → F22 (two links each); F10 → F23 → F32 → F42 (ended by deleting the inference);
F33 → F43 (two links). Earlier: F10 → F23 → F32 (three links, ended by a cut: the page
records its own evidence instead of the snapshot inferring it).

Codex's E-E-A-T question settled by Google's own page: "E-E-A-T itself isn't a specific ranking
factor" (Search Central, "Creating helpful, reliable, people-first content", updated 2026-10-05);
the instructions now quote it rather than claim more.

Breakage check: the nine round-1 tests that existed then, plus the updated ones, were run on
f3cea24's code: every one fails there except the failed-save test, which passes there too (round 1
saved after the git check, so nothing was kept either). The link-warning test (F18) was added
afterwards and was not part of that run. Test records after the fixes: `make test` 274 OK, `make
check` exit 0.
